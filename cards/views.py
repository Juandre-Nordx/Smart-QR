import io
import qrcode
import qrcode.image.svg
from django.contrib.admin.views.decorators import staff_member_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .forms import CompanyForm, PersonForm
from .models import Company, Person

def health(request): return JsonResponse({"status": "ok"})

@staff_member_required
def dashboard(request):
    companies = Company.objects.prefetch_related("people")
    return render(request, "cards/dashboard.html", {"companies": companies})

@staff_member_required
def company_dashboard(request, pk):
    company = get_object_or_404(Company.objects.prefetch_related("people"), pk=pk)
    return render(request, "cards/company_dashboard.html", {"company": company})

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
