from django.shortcuts import render, redirect
from django.contrib import messages


def home(request):
    return render(request, 'core/home.html')


def about(request):
    return render(request, 'core/about.html')


def team(request):
    team_members = [
        {
            'name': 'Mehakdeep Singh',
            'role': 'Co-Founder & Community Lead',
            'bio': 'Passionate about building bridges between Punjabis across India. Mehakdeep leads community strategy, events, and growth initiatives for Panjabi in Bengaluru.',
            'instagram': 'https://www.instagram.com/mehak.shokar/',
            'instagram_handle': '@mehak.shokar',
            'initials': 'MS',
            'color': 'gold',
        },
        {
            'name': 'Karun Pabbi',
            'role': 'Co-Founder & Operations Head',
            'bio': "A connector at heart, Karun drives operations, networking events, and career development programs to make every member's experience exceptional.",
            'instagram': 'https://www.instagram.com/karunpabbi/',
            'instagram_handle': '@karunpabbi',
            'initials': 'KP',
            'color': 'navy',
        },
        {
            'name': 'Karanbir Singh',
            'role': 'Co-Founder & Creative Director',
            'bio': 'The creative force behind the brand, Karanbir shapes the visual identity, storytelling, and cultural vision of Panjabi in Bengaluru.',
            'instagram': 'https://www.instagram.com/kabirunfiltered/',
            'instagram_handle': '@kabirunfiltered',
            'initials': 'KS',
            'color': 'maroon',
        },
    ]
    return render(request, 'core/team.html', {'team_members': team_members})


def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if name and email and subject and message:
            messages.success(request, f"Thank you {name}! Your message has been received. We'll get back to you shortly.")
        else:
            messages.error(request, 'Please fill in all required fields.')
        return redirect('contact')
    return render(request, 'core/contact.html')


def join(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()

        if name and email and phone:
            messages.success(request, f"Welcome to the family, {name}! 🎉 We'll reach out to you at {email} with next steps.")
        else:
            messages.error(request, 'Please fill in all required fields.')
        return redirect('join')
    return render(request, 'core/join.html')
