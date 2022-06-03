import os
from tkinter import W
from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.http import HttpResponse, HttpResponseServerError, HttpResponseNotFound
from django.core.files import File
# Django transaction system so we can use @transaction.atomic
from django.db import transaction
from django.conf import settings

from strack.forms import LoginForm, RegisterForm, ProfileForm, AssemblyCodeForm
from strack.models import AssemblyCode, Profile
from strack.helpers import LLDBSubprocess, FileStorageHandler
import json
from os.path import exists
import shutil 

def interpreter_page(request):
    context = {}
    if request.method == 'GET':
        context['form'] = AssemblyCodeForm()
        context['code_ready'] = False
        return render(request, './interpreter.html', context)

    form = AssemblyCodeForm(request.POST, request.FILES)
    if not form.is_valid():
        context['form'] = form
        return render(request, './interpreter.html', context)

    user = request.user
    if not request.user.is_authenticated:
        try:
            user = User.objects.get(pk=1)
        except User.DoesNotExist:
            return HttpResponseServerError()

    c_file = form.cleaned_data['code_file']
    file_name = form.cleaned_data['title'].strip().replace(' ', '_')
    fs = FileStorageHandler(c_file, file_name)
    code_path = fs.save_file()
    exe_path = fs.get_local_executable_path()
    error_path = code_path.replace('.c', '.err')
    fs.compile()
    
    if (not exists(exe_path)):
        context = handle_compile_fail(code_path, error_path, form)
        return render(request, './interpreter.html', context)
    
    state_path = fs.get_local_state_path()
    lldb_sp = LLDBSubprocess(exe_path, form.cleaned_data.get('timeout'))
    lldb_sp.start()

    if (not exists(state_path)):
        context = handle_execution_fail(state_path, code_path, exe_path, error_path, form)
        return render(request, './interpreter.html', context)

    model_id = create_asm_model(file_name, code_path, exe_path, state_path, error_path, user, form)

    return code_page(request, model_id)

def handle_compile_fail(code_path, error_path, form):
    context = {}
    error_file = open(error_path, 'r')
    context['form'] = form
    context['code_ready'] = False
    context['error'] = 'File compilation failed. Error message:\n' + error_file.read()
    os.remove(code_path)
    os.remove(error_path)
    return context

def handle_execution_fail(state_path, code_path, exe_path, error_path, form):
    context = {}
    if exists(state_path.replace('.json', '.to')):
        context['error'] = 'File execution timed out'
        os.remove(state_path.replace('.json', '.to'))
    else:
        context['error'] = 'File execution failed'
    os.remove(code_path)
    os.remove(exe_path)
    os.remove(error_path)
    shutil.rmtree(exe_path + '.dSYM')
    context['form'] = form
    context['code_ready'] = False
    return context

def create_asm_model(file_name, code_path, exe_path, state_path, error_path, user, form):
    file_pref = file_name.split('.')[0]
    code_f = open(code_path, 'rb')
    code_file_text = code_f.read()
    code_file_text = str(code_file_text)[2:-1]
    state_f = open(state_path, 'rb')

    asm_model = AssemblyCode(title=form.cleaned_data['title'],
                             file_prefix=file_pref,
                             code_file=File(code_f, code_path),
                             code_text=code_file_text,
                             state_file=File(state_f, state_path),
                             creation_time=timezone.now(),
                             created_by=user)
    asm_model.save()
    code_f.close()
    state_f.close()
    
    os.remove(state_path)
    os.remove(code_path)
    os.remove(error_path)
    os.remove(exe_path)
    shutil.rmtree(exe_path + '.dSYM')
    return asm_model.id

def login_action(request):
    context = {
        'is_at_login_page': True,
    }

    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = LoginForm()
        return render(request, 'basic/login.html', context)

    # Creates a bound form from the request POST parameters and makes the
    # form available in the request context dictionary.
    form = LoginForm(request.POST)
    context['form'] = form

    # Validates the form.
    if not form.is_valid():
        return render(request, 'basic/login.html', context)

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)
    return redirect(reverse('interpreter'))


def logout_action(request):
    logout(request)
    return redirect(reverse('interpreter'))


@transaction.atomic
def register_action(request):
    context = {}
    # Just display the registration form if this is a GET request.
    if request.method == 'GET':
        context['form'] = RegisterForm()
        return render(request, 'basic/register.html', context)

    form = RegisterForm(request.POST)
    context['form'] = form

    if not form.is_valid():
        return render(request, 'basic/register.html', context)

    # At this point, the form data is valid.  Register and login the user.
    new_user = User.objects.create_user(username=form.cleaned_data['username'],
                                        password=form.cleaned_data['password'],
                                        email=form.cleaned_data['email'],
                                        first_name=form.cleaned_data['first_name'],
                                        last_name=form.cleaned_data['last_name'])
    new_user.save()

    new_user = authenticate(username=form.cleaned_data['username'],
                            password=form.cleaned_data['password'])

    login(request, new_user)

    new_profile = Profile()
    new_profile.profile_id = request.user.id
    new_profile.created_by = request.user
    new_profile.creation_time = timezone.now()
    new_profile.update_time = timezone.now()
    new_profile.save()

    return redirect(reverse('interpreter'))


def oauth_profile_creation(request):
    try:
        Profile.objects.get(pk=request.user.id)
    except Profile.DoesNotExist:
        new_profile = Profile()
        new_profile.profile_id = request.user.id
        new_profile.created_by = request.user
        new_profile.creation_time = timezone.now()
        new_profile.update_time = timezone.now()
        new_profile.save()
    finally:
        return redirect(reverse('interpreter'))

def add_anonymous_user(request):
    try:
        User.objects.get(pk=1)
    except User.DoesNotExist:
        new_user = User.objects.create_user(username='anonymous',
                                        password='anonymous_password',
                                        email='',
                                        first_name='anonymous',
                                        last_name='user')
        new_user.save()

        new_profile = Profile()
        new_profile.profile_id = 1
        new_profile.created_by = new_user
        new_profile.creation_time = timezone.now()
        new_profile.update_time = timezone.now()
        new_profile.save()
    finally:
        return HttpResponseNotFound()


####################################################
#                      Profile                     #
####################################################
@login_required
def get_photo(request, id):
    item = get_object_or_404(Profile, profile_id=id)
    print('Picture #{} fetched from db: {} (type={})'.format(id, item.picture, type(item.picture)))

    # Maybe we don't need this check as form validation requires a picture be uploaded.
    # But someone could have delete the picture leaving the DB with a bad references.
    if not item.picture:
        return HttpResponseNotFound()

    return HttpResponse(item.picture, content_type=item.content_type)

@login_required
def profile_page(request, id):
    if id == 1:
        return HttpResponseNotFound()

    profile = get_object_or_404(Profile, profile_id=id)
    form = ProfileForm(initial={'bio_content': profile.bio_content})
    context = {
        'profile': profile,
        'form': form,
        'codes': AssemblyCode.objects.filter(created_by=profile.created_by).order_by('-creation_time')
    }

    if request.method == 'GET':
        return render(request, 'user/profile.html', context)

    new_form = ProfileForm(request.POST, request.FILES, instance=profile)

    if not new_form.is_valid():
        context['form'] = new_form
    else:
        # Must copy content_type into a new model field because the model
        # FileField will not store this in the database.  (The uploaded file
        # is actually a different object than what's return from a DB read.)
        pic = new_form.cleaned_data['picture']
        print('Uploaded picture: {} (type={})'.format(pic, type(pic)))

        profile.content_type = new_form.cleaned_data['picture'].content_type
        profile.update_time = timezone.now()

        new_form.save()

        context['profile'] = Profile.objects.get(pk=id)
        context['form'] = new_form

    return render(request, 'user/profile.html', context)


@login_required
def follow_action(request, id):
    user_to_follow = get_object_or_404(User, pk=id)
    request.user.profile.following.add(user_to_follow)
    request.user.profile.save()
    return redirect('profile', id=id)

@login_required
def unfollow_action(request, id):
    user_to_unfollow = get_object_or_404(User, pk=id)
    request.user.profile.following.remove(user_to_unfollow)
    request.user.profile.save()
    return redirect('profile', id=id)

#TODO: AJAX
@login_required
def profile_star_action(request, pid, cid):
    code_to_star = get_object_or_404(AssemblyCode, pk=cid)
    request.user.profile.starring.add(code_to_star)
    request.user.profile.save()
    return redirect('profile', id=pid)

#TODO: AJAX
@login_required
def profile_unstar_action(request, pid, cid):
    code_to_unstar = get_object_or_404(AssemblyCode, pk=cid)
    request.user.profile.starring.remove(code_to_unstar)
    request.user.profile.save()
    return redirect('profile', id=pid)

@login_required
def profile_delete_code(request, pid, cid):
    if (pid != request.user.id):
        return HttpResponseNotFound()

    code = get_object_or_404(AssemblyCode, pk=cid)
    if (code.created_by != request.user):
        return HttpResponseNotFound()

    code.delete()
    context = {}
    context['codes'] = AssemblyCode.objects.all().order_by('-creation_time')

    return redirect('profile', id=pid)


####################################################
#                     DashBoard                    #
####################################################
@login_required
def dashboard_page(request):
    context = {}
    context['codes'] = AssemblyCode.objects.all().order_by('-creation_time')
    no_following_code = True
    for following in request.user.profile.following.all():
        if following.assemblycode_set.count() > 0:
            no_following_code = False
            break
    context['no_following_code'] = no_following_code
    return render(request, 'user/dashboard.html', context)

@login_required
def download_code(request, id):
    code = get_object_or_404(AssemblyCode, pk=id)
    response = HttpResponse(code.code_file, content_type='text/plain')
    response['Content-Disposition'] = 'attachment; filename=%s' % (code.title.replace('_', ' ') + '.c')

    return response

#TODO: AJAX
@login_required
def star_action(request, id):
    code_to_star = get_object_or_404(AssemblyCode, pk=id)
    request.user.profile.starring.add(code_to_star)
    request.user.profile.save()
    return redirect('dashboard')

#TODO: AJAX
@login_required
def unstar_action(request, id):
    code_to_unstar = get_object_or_404(AssemblyCode, pk=id)
    request.user.profile.starring.remove(code_to_unstar)
    request.user.profile.save()
    return redirect('dashboard')

#TODO: AJAX
@login_required
def code_page_star_action(request, id):
    code_to_star = get_object_or_404(AssemblyCode, pk=id)
    request.user.profile.starring.add(code_to_star)
    request.user.profile.save()
    return redirect('code', id=id)


#TODO: AJAX
@login_required
def code_page_unstar_action(request, id):
    code_to_unstar = get_object_or_404(AssemblyCode, pk=id)
    request.user.profile.starring.remove(code_to_unstar)
    request.user.profile.save()
    return redirect('code', id=id)


def code_page(request, id):
    context = {}
    code = get_object_or_404(AssemblyCode, pk=id)
    if not request.user.is_authenticated and code.created_by.id != 1:
        return HttpResponseNotFound()
    f = open(code.state_file.path, 'rb')
    state_info = json.load(f)
    state_info = json.dumps(state_info)
    # code_text_list = code.code_text.split('\n')

    context['code_ready'] = True
    context['form'] = AssemblyCodeForm()
    context['title'] = code.title
    context['code_file'] = code.code_file.path.replace(str(settings.MEDIA_ROOT), '').replace('strack/static/file_storage/', '')
    context['code_text'] = code.code_text
    context['asm_code_id'] = id
    context['asm_state'] = state_info
    context['code'] = code
    return render(request, './interpreter.html', context)
