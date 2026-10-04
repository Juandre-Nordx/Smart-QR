import io
from decimal import Decimal
from PIL import Image
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from .models import Company, Person

@override_settings(PUBLIC_BASE_URL="https://cards.example.test")
class CardTests(TestCase):
    def setUp(self):
        self.company = Company.objects.create(name="Acme", billing_email="private@billing.test", billing_contact_name="Private Person")
        self.person = Person.objects.create(company=self.company, first_name="Zoë", last_name="Smith, Jr", email="zoe@example.test", biography="Hello", address="One; Road", mobile_phone="0123")
        self.staff = get_user_model().objects.create_user("staff", password="test-pass", is_staff=True)
        self.company_user = get_user_model().objects.create_user("acme", password="company-pass")
        self.company.dashboard_users.add(self.company_user)
    def test_dashboard_requires_staff(self):
        self.assertEqual(self.client.get(reverse("cards:dashboard")).status_code, 302)
        self.client.login(username="staff", password="test-pass")
        self.assertEqual(self.client.get(reverse("cards:dashboard")).status_code, 200)
    def test_company_dashboard_lists_only_company_people(self):
        other_company = Company.objects.create(name="Other Co")
        other_person = Person.objects.create(company=other_company, first_name="Not", last_name="Shown")
        self.client.login(username="staff", password="test-pass")
        response = self.client.get(reverse("cards:company-dashboard", args=[self.company.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.person.full_name)
        self.assertContains(response, self.person.position or "Team member")
        self.assertContains(response, reverse("cards:qr", args=[self.person.public_id, "svg"]))
        self.assertNotContains(response, other_person.full_name)

    def test_company_dashboard_requires_staff(self):
        response = self.client.get(reverse("cards:company-dashboard", args=[self.company.pk]))
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('cards:company-dashboard', args=[self.company.pk])}", fetch_redirect_response=False)

    def test_company_user_sees_only_assigned_company(self):
        other_company = Company.objects.create(name="Private Other Co")
        other_person = Person.objects.create(company=other_company, first_name="Hidden", last_name="Person")
        self.client.login(username="acme", password="company-pass")

        dashboard = self.client.get(reverse("cards:dashboard"))
        self.assertRedirects(dashboard, reverse("cards:company-dashboard", args=[self.company.pk]))

        company_dashboard = self.client.get(reverse("cards:company-dashboard", args=[self.company.pk]))
        self.assertContains(company_dashboard, self.person.full_name)
        self.assertContains(company_dashboard, "Share card")
        self.assertContains(company_dashboard, reverse("cards:company-person-create", args=[self.company.pk]))
        self.assertContains(company_dashboard, self.person.permanent_url())
        self.assertNotContains(company_dashboard, reverse("cards:person-edit", args=[self.person.pk]))
        self.assertEqual(self.client.get(reverse("cards:company-dashboard", args=[other_company.pk])).status_code, 404)
        self.assertNotContains(company_dashboard, other_person.full_name)

    def test_company_user_can_add_person_only_to_assigned_company(self):
        self.company.user_limit = 2
        self.company.save(update_fields=["user_limit"])
        other_company = Company.objects.create(name="Private Other Co")
        self.client.login(username="acme", password="company-pass")

        add_url = reverse("cards:company-person-create", args=[self.company.pk])
        response = self.client.post(add_url, {"first_name": "New", "last_name": "Teammate", "email": "new@example.test"})
        person = Person.objects.get(first_name="New", last_name="Teammate")
        self.assertRedirects(response, reverse("cards:company-dashboard", args=[self.company.pk]))
        self.assertEqual(person.company, self.company)
        self.assertTrue(person.is_active)
        self.assertEqual(self.client.get(reverse("cards:company-person-create", args=[other_company.pk])).status_code, 404)

    def test_company_user_cannot_add_person_past_plan_limit(self):
        self.client.login(username="acme", password="company-pass")
        response = self.client.post(
            reverse("cards:company-person-create", args=[self.company.pk]),
            {"first_name": "Over", "last_name": "Limit"},
        )
        self.assertContains(response, "User limit reached")
        self.assertFalse(Person.objects.filter(first_name="Over", last_name="Limit").exists())

    def test_company_user_cannot_access_staff_management(self):
        self.client.login(username="acme", password="company-pass")
        for url in (
            reverse("cards:people"),
            reverse("cards:company-create"),
            reverse("cards:company-edit", args=[self.company.pk]),
            reverse("cards:person-create"),
            reverse("cards:person-edit", args=[self.person.pk]),
        ):
            self.assertRedirects(self.client.get(url), f"{reverse('admin:login')}?next={url}", fetch_redirect_response=False)

    def test_company_login_page(self):
        response = self.client.get(reverse("login"))
        self.assertContains(response, "Login to QRD")
        login = self.client.post(reverse("login"), {"username": "acme", "password": "company-pass"})
        self.assertRedirects(login, reverse("cards:dashboard"), fetch_redirect_response=False)

    def test_home_renders_landing_page_and_pricing(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Your business card")
        self.assertContains(response, '<div class="price"><span>R</span>80', html=False)
    def test_public_card_hides_account_navigation_from_logged_in_users(self):
        self.client.login(username="staff", password="test-pass")
        response = self.client.get(self.person.get_absolute_url())
        self.assertNotContains(response, ">Companies<")
        self.assertNotContains(response, ">People<")
        self.assertNotContains(response, ">Log out<")

    def test_unavailable_card_hides_account_navigation_from_logged_in_users(self):
        self.person.is_active = False
        self.person.save()
        self.client.login(username="staff", password="test-pass")
        response = self.client.get(self.person.get_absolute_url())
        self.assertNotContains(response, ">Companies<", status_code=410)
        self.assertNotContains(response, ">People<", status_code=410)
        self.assertNotContains(response, ">Log out<", status_code=410)

    def test_url_stable_after_edit(self):
        url = self.person.permanent_url(); self.person.first_name="Changed"; self.person.save()
        self.assertEqual(url, self.person.permanent_url())
    def test_qr_formats_and_payload(self):
        png=self.client.get(reverse("cards:qr", args=[self.person.public_id,"png"])); self.assertEqual(png["Content-Type"], "image/png"); self.assertTrue(png.content.startswith(b"\x89PNG"))
        svg=self.client.get(reverse("cards:qr", args=[self.person.public_id,"svg"])); self.assertEqual(svg["Content-Type"], "image/svg+xml"); self.assertIn(b"<svg", svg.content)
        import qrcode
        from unittest.mock import patch
        with patch("cards.views.qrcode.make", wraps=qrcode.make) as make:
            self.client.get(reverse("cards:qr", args=[self.person.public_id,"png"])); self.assertEqual(make.call_args.args[0], self.person.permanent_url())
    def test_vcard_download_escaping_and_crlf(self):
        response=self.client.get(reverse("cards:vcard", args=[self.person.public_id])); body=response.content
        self.assertIn("attachment", response["Content-Disposition"]); self.assertIn(b"BEGIN:VCARD\r\n", body); self.assertIn("Smith\\, Jr".encode(), body); self.assertIn(b"One\\; Road", body)
    def test_inactive_is_private(self):
        self.person.is_active=False; self.person.save(); response=self.client.get(self.person.get_absolute_url())
        self.assertEqual(response.status_code, 410); self.assertNotContains(response, self.person.email, status_code=410); self.assertNotContains(response, "private@billing.test", status_code=410)
        self.assertEqual(self.client.get(reverse("cards:vcard", args=[self.person.public_id])).status_code, 404)
    def test_counts_and_billing(self):
        Person.objects.create(company=self.company, first_name="Off", last_name="Line", is_active=False)
        self.assertEqual(self.company.active_card_count, 1); self.assertEqual(self.company.monthly_total, Decimal("90.00"))

    def test_self_service_signup_creates_company_and_admin(self):
        self.client.post(reverse("cards:signup", args=["company"]), {"company_name": "Nova Labs", "industry": "Technology"})
        self.client.post(reverse("cards:signup", args=["admin"]), {"full_name": "Ada Lovelace", "email": "ada@nova.test", "password": "secure-password-123"})
        self.client.post(reverse("cards:signup", args=["users"]), {"user_count": 7})
        summary = self.client.get(reverse("cards:signup", args=["summary"]))
        self.assertContains(summary, "R150")
        self.client.post(reverse("cards:signup", args=["summary"]))
        response = self.client.post(reverse("cards:signup", args=["payment"]), {"confirm": "on"})
        company = Company.objects.get(name="Nova Labs")
        self.assertRedirects(response, reverse("cards:signup-success", args=[company.pk]))
        self.assertEqual(company.industry, "Technology")
        self.assertEqual(company.user_limit, 7)
        self.assertTrue(company.dashboard_users.filter(username="ada@nova.test").exists())
    def test_image_validation(self):
        bad=SimpleUploadedFile("bad.gif", b"not an image", content_type="image/gif"); self.person.photo=bad
        with self.assertRaises(ValidationError): self.person.full_clean()
        data=io.BytesIO(); Image.new("RGB",(2,2)).save(data,"PNG"); good=SimpleUploadedFile("ok.png",data.getvalue(),content_type="image/png"); self.person.photo=good; self.person.full_clean()
    @override_settings(DEBUG=False, SERVE_MEDIA=True)
    def test_uploaded_photo_is_served_in_production(self):
        data = io.BytesIO()
        Image.new("RGB", (2, 2)).save(data, "PNG")
        self.person.photo = SimpleUploadedFile("profile.png", data.getvalue(), content_type="image/png")
        self.person.save()
        self.addCleanup(self.person.photo.storage.delete, self.person.photo.name)
        response = self.client.get(self.person.photo.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), data.getvalue())

    def test_health(self):
        response=self.client.get(reverse("cards:health")); self.assertEqual(response.status_code,200); self.assertEqual(response.json(),{"status":"ok"})
