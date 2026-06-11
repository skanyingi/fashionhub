from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib.auth.forms import PasswordResetForm



# First time visitors view welcome screen before homepage
def onboarding(request):
    return render(request, "shop/onboarding.html")

# Marks onboarding complete so user doen't view again
def complete_onboarding(request):
    request.session["has_seen_onboarding"] = True  # stores flag in session so onboarding is not shown again 
    next_url = request.GET.get("next", "index")
    return redirect(next_url)



# handl new user registration
def register(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")

        print("Username:", username)
        print("Email:", email)
        print("Password:", password)
        print("Confirm Password:", confirm_password)
        print(username)

        if password != confirm_password:
            return HttpResponse(
                '<div style="color: red; margin-bottom: 10px"> Passwords do not match</div>'
            )

        if User.objects.filter(username=username).exists():
            return HttpResponse(
                '<div style="color: red; margin-bottom: 10px"> Username already taken</div>'
            )
        User.objects.create_user(username=username, email=email, password=password) # Create new user account
        # Use HTMX redirect to navigate to login page
        response = HttpResponse("redirect... ")
        response["HX-Redirect"] = "/login"
        return response
    return render(request, "shop/register.html")


# Handle user authentication and login
def login_user(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        # Check if username exists in the database
        try:
            User.objects.get(username=username)
            # Username exists, now check password
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get("next", "index")
                response = HttpResponse("")
                # Handle both URLs and full path URLs for redirect
                if "/" not in next_url:
                    response["HX-Redirect"] = reverse(next_url)
                else:
                    response["HX-Redirect"] = next_url
                return response
            else:
                # Username exists but password is wrong
                return HttpResponse(
                    '<div style="color:red; padding-bottom: 20px;">Invalid password</div>'
                )
        except User.DoesNotExist:
            # username does not exist in the database
            return HttpResponse(
                '<div style="color:red; padding-bottom: 20px;">Invalid username</div>'
            )
    #GET request here and display login form with password reset option
    form = PasswordResetForm()
    return render(request, "shop/login.html", {"form": form})





#Logs out current user and redirect to homepage
def logout_view(request):
    logout(request)
    return redirect("index")
