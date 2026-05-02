import pytest
import uuid
import re
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8000"


def test_registration_and_login_flow(page: Page):
    """Test Register -> Login -> Logout flow"""
    short_user = f"u{uuid.uuid4().hex[:4]}"

    # 1. Register
    page.goto(f"{BASE_URL}/register")
    page.fill('input[name="username"]', short_user)
    page.fill('input[name="email"]', f"{short_user}@test.com")
    page.fill('input[name="password"]', "pass1234")
    page.fill('input[name="confirm_password"]', "pass1234")
    page.click('button[type="submit"]')

    # 2. Login
    page.wait_for_url(f"{BASE_URL}/login")
    page.fill('input[name="username"]', short_user)
    page.fill('input[name="password"]', "pass1234")
    page.click('button[type="submit"]')

    # 3. Verify login - My Receipts only appears when authenticated
    page.wait_for_url(f"{BASE_URL}/", timeout=10000)
    expect(page.get_by_text("My Receipts")).to_be_visible(timeout=10000)

    # 4. Logout via direct POST using page.context.request (shares browser cookies)
    # page.request is isolated and has NO session cookie - always use page.context.request
    cookies = {c["name"]: c["value"] for c in page.context.cookies()}
    csrf = cookies.get("csrftoken", "")
    page.context.request.post(
        f"{BASE_URL}/logout/",
        headers={
            "X-CSRFToken": csrf,
            "Referer": f"{BASE_URL}/",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data=f"csrfmiddlewaretoken={csrf}",
    )

    # 5. Confirm logged out - cart page should still work (no login required)
    # but my-receipts redirects to login if @login_required is added (see fix below)
    # For now, verify session is gone by checking the home page renders login state
    page.goto(f"{BASE_URL}/")
    # My Receipts disappears from sidenav when logged out
    expect(page.get_by_text("My Receipts")).not_to_be_visible(timeout=10000)


def test_shopping_cart_flow(page: Page):
    """Test browsing and adding to cart"""
    page.goto(f"{BASE_URL}/women")

    page.locator(".product-card-modern a").first.click()
    page.wait_for_url(re.compile(r".*/product/.*"))

    size_btn = page.locator(".size-option").first
    size_btn.wait_for(state="visible")
    size_btn.click()

    page.locator("#mainAddToCartForm button").click()

    page.wait_for_url(re.compile(r".*/cart.*"), timeout=15000)
    expect(page.locator(".cart-item-card").first).to_be_visible()


def test_search_functionality(page: Page):
    """Simple search test"""
    page.goto(f"{BASE_URL}/")
    page.fill('input[name="q"]', "Shoes")
    page.press('input[name="q"]', "Enter")

    page.wait_for_url(re.compile(r".*search.*"))
    expect(page.locator(".product-card-modern").first).to_be_visible()