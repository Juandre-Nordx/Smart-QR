import io
import qrcode
import qrcode.image.svg
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model, login
from django.db import transaction
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import AdminSignupForm, CompanyForm, CompanyPersonForm, CompanySignupForm, PaymentConfirmationForm, PersonForm, SeatsSignupForm
from .models import Company, Person

def health(request): return JsonResponse({"status": "ok"})

def landing(request):
    return render(request, "cards/landing.html")

SIGNUP_STEPS = (
    ("company", CompanySignupForm, "Company"),
    ("admin", AdminSignupForm, "Admin"),
    ("users", SeatsSignupForm, "Users"),
    ("summary", None, "Summary"),
    ("payment", PaymentConfirmationForm, "Payment"),
)

def signup(request, step="company"):
    step_names = [item[0] for item in SIGNUP_STEPS]
    if step not in step_names:
        raise Http404
    step_index = step_names.index(step)
    signup_data = request.session.get("signup_data", {})
    if step_index and not all(name in signup_data for name in step_names[:step_index] if name != "summary"):
        return redirect("cards:signup", step="company")
    form_class = SIGNUP_STEPS[step_index][1]
    form = form_class(request.POST or None, initial=signup_data.get(step)) if form_class else None
    if request.method == "POST":
        if form and form.is_valid():
            signup_data[step] = form.cleaned_data
            request.session["signup_data"] = signup_data
            if step == "payment":
                with transaction.atomic():
                    admin = signup_data["admin"]
                    user = get_user_model().objects.create_user(
                        username=admin["email"], email=admin["email"], password=admin["password"]
                    )
                    first_name, _, last_name = admin["full_name"].strip().partition(" ")
                    user.first_name, user.last_name = first_name, last_name
                    user.save(update_fields=["first_name", "last_name"])
                    company = Company.objects.create(
                        name=signup_data["company"]["company_name"],
                        industry=signup_data["company"]["industry"],
                        billing_email=admin["email"],
                        billing_contact_name=admin["full_name"],
                        user_limit=signup_data["users"]["user_count"],
                    )
                    company.dashboard_users.add(user)
                del request.session["signup_data"]
                login(request, user)
                messages.success(request, "Your QRD workspace is ready.")
                return redirect("cards:signup-success", pk=company.pk)
            return redirect("cards:signup", step=step_names[step_index + 1])
        if step == "summary":
            return redirect("cards:signup", step="payment")
    user_count = signup_data.get("users", {}).get("user_count", 0)
    context = {
        "form": form,
        "step": step,
        "step_index": step_index + 1,
        "steps": SIGNUP_STEPS,
        "signup_data": signup_data,
        "user_count": user_count,
        "monthly_total": 80 + (10 * user_count),
    }
    return render(request, "cards/signup.html", context)

@login_required
def signup_success(request, pk):
    company = get_object_or_404(Company.objects.filter(dashboard_users=request.user), pk=pk)
    return render(request, "cards/signup_success.html", {"company": company})

@login_required
def dashboard(request):
    companies = Company.objects.prefetch_related("people")
    if not request.user.is_staff:
        companies = companies.filter(dashboard_users=request.user)
        company = companies.first()
        if company and companies.count() == 1:
            return redirect("cards:company-dashboard", pk=company.pk)
    return render(request, "cards/dashboard.html", {"companies": companies})

@login_required
def company_dashboard(request, pk):
    companies = Company.objects.prefetch_related("people")
    if not request.user.is_staff:
        companies = companies.filter(dashboard_users=request.user)
    company = get_object_or_404(companies, pk=pk)
    return render(request, "cards/company_dashboard.html", {"company": company})

@login_required
def company_person_create(request, pk):
    companies = Company.objects.all()
    if not request.user.is_staff:
        companies = companies.filter(dashboard_users=request.user)
    company = get_object_or_404(companies, pk=pk)
    at_capacity = not request.user.is_staff and company.people.count() >= company.user_limit
    form = CompanyPersonForm(request.POST or None, request.FILES or None)
    if request.method == "POST":
        if at_capacity:
            form.add_error(None, "Your plan has reached its user limit. Contact QRD to add more users.")
        elif form.is_valid():
            person = form.save(commit=False)
            person.company = company
            person.save()
            messages.success(request, f"{person.full_name}'s digital card is ready.")
            return redirect("cards:company-dashboard", pk=company.pk)
    return render(request, "cards/person_create.html", {"form": form, "company": company, "at_capacity": at_capacity})

@staff_member_required
def people(request): return render(request, "cards/person_list.html", {"people": Person.objects.select_related("company")})

def _edit(request, form_class, template, instance=None):
    form = form_class(request.POST or None, request.FILES or None, instance=instance)
    if request.method == "POST" and form.is_valid(): form.save(); return redirect("cards:dashboard")
    return render(request, template, {"form": form, "object": instance})

@staff_member_required
def company_create(request): return _edit(request, CompanyForm, "cards/form.html")
@staff_member_required
def company_edit(request, pk): return _edit(request, CompanyForm, "cards/form.html", get_object_or_404(Company, pk=pk))
@staff_member_required
def person_create(request): return _edit(request, PersonForm, "cards/form.html")
@staff_member_required
def person_edit(request, pk): return _edit(request, PersonForm, "cards/form.html", get_object_or_404(Person, pk=pk))

@staff_member_required
@require_POST
def toggle_person(request, pk):
    person = get_object_or_404(Person, pk=pk); person.is_active = not person.is_active; person.save(update_fields=["is_active", "updated_at"])
    return redirect("cards:people")

def public_card(request, public_id):
    person = get_object_or_404(Person.objects.select_related("company"), public_id=public_id)
    if not person.is_active: return render(request, "cards/unavailable.html", status=410)
    return render(request, "cards/public_card.html", {"person": person})

def _active(public_id): return get_object_or_404(Person.objects.select_related("company"), public_id=public_id, is_active=True)
def qr_download(request, public_id, kind):
    if kind not in {"png", "svg"}: raise Http404
    person = _active(public_id)
    factory = qrcode.image.svg.SvgPathImage if kind == "svg" else None
    image = qrcode.make(person.permanent_url(), image_factory=factory)
    output = io.BytesIO(); image.save(output)
    content_type = "image/svg+xml" if kind == "svg" else "image/png"
    response = HttpResponse(output.getvalue(), content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="card-{person.public_id}.{kind}"'
    return response

def _esc(value):
    return str(value or "").replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "").replace(";", "\\;").replace(",", "\\,")
def _fold(line):
    parts=[]
    while len(line.encode("utf-8")) > 75:
        end=75
        while len(line[:end].encode("utf-8")) > 75: end-=1
        parts.append(line[:end]); line=" "+line[end:]
    parts.append(line); return "\r\n".join(parts)
def vcard(request, public_id):
    p = _active(public_id); c = p.company
    lines = ["BEGIN:VCARD", "VERSION:3.0", f"N:{_esc(p.last_name)};{_esc(p.first_name)};;;", f"FN:{_esc(p.full_name)}", f"ORG:{_esc(c.name)}"]
    values = [("TITLE", p.position), ("TEL;TYPE=CELL", p.mobile_phone), ("TEL;TYPE=WORK", p.work_phone), ("TEL;TYPE=CELL,WHATSAPP", p.whatsapp_number), ("EMAIL;TYPE=INTERNET", p.email), ("URL", p.website or c.website), ("ADR;TYPE=WORK", f";;{p.address or c.address};;;;")]
    lines += [f"{key}:{_esc(value)}" for key, value in values if value]
    lines.append("END:VCARD")
    body = "\r\n".join(_fold(x) for x in lines) + "\r\n"
    response = HttpResponse(body.encode("utf-8"), content_type="text/vcard; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{p.public_id}.vcf"'; return response
