import pytest
import re
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8000"

def test_admin_dashboard_access(page: Page):
    """Test admin access to inventory and reports"""
    page.goto(f"{BASE_URL}/admin/login/?next=/reports/")
    page.fill('input[name="username"]', "admin")
    page.fill('input[name="password"]', "admin123")
    page.get_by_role("button", name=re.compile("Log in", re.I)).click()
    
    # Wait for navigation to complete
    page.wait_for_load_state("networkidle")
    expect(page).not_to_have_url(re.compile(".*admin/login.*"))    
    page.goto(f"{BASE_URL}/reports/")
    expect(page.get_by_text("Sales Summary Report")).to_be_visible()
