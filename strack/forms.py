from django import forms

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

from strack.models import Profile, AssemblyCode
MAX_UPLOAD_SIZE = 2500000

class LoginForm(forms.Form):
    username = forms.CharField(max_length = 20)
    password = forms.CharField(max_length = 200, widget = forms.PasswordInput())

    # Customizes form validation for properties that apply to more
    # than one field.  Overrides the forms.Form.clean function.
    def clean(self):
        # Calls our parent (forms.Form) .clean function, gets a dictionary
        # of cleaned data as a result
        cleaned_data = super().clean()

        # Confirms that the two password fields match
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        user = authenticate(username=username, password=password)
        if not user:
            raise forms.ValidationError("Invalid username/password")

        # We must return the cleaned data we got from our parent.
        return cleaned_data


class RegisterForm(forms.Form):
    username          = forms.CharField(max_length = 20)
    password          = forms.CharField(max_length = 200,
                                        label='Password',
                                        widget = forms.PasswordInput())
    confirm_password  = forms.CharField(max_length = 200,
                                        label='Confirm password',
                                        widget = forms.PasswordInput())
    email             = forms.CharField(max_length=50,
                                        widget = forms.EmailInput())
    first_name        = forms.CharField(max_length=20)
    last_name         = forms.CharField(max_length=20)

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password')
        password2 = cleaned_data.get('confirm_password')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords did not match.")

        return cleaned_data

    # Customizes form validation for the username field.
    def clean_username(self):
        # Confirms that the username is not already present in the User model database.
        username = self.cleaned_data.get('username')
        if User.objects.select_for_update().filter(username__exact=username):
            raise forms.ValidationError("Username is already taken.")

        # We must return the cleaned data we got from the cleaned_data dictionary
        return username


class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ('picture', 'bio_content')
        labels = {
            'picture': 'Profile Picture',
            'bio_content': 'BIO',
        },
        widgets = {
            'picture': forms.FileInput(attrs={'height' : 40, 'width' : 40, 'id': 'id_profile_picture', 'accept': 'accept'}),
            'bio_content': forms.Textarea(attrs={'cols': 40, 'rows': 5, 'id': 'id_bio_input_text', 'placeholder': "Add your bio!"}),
        }

    def clean_picture(self):
        picture = self.cleaned_data['picture']
        if not picture or not hasattr(picture, 'content_type'):
            raise forms.ValidationError('You must upload a picture')
        if not picture.content_type or not picture.content_type.startswith('image'):
            raise forms.ValidationError('File type is not image')
        if picture.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError('File too big (max size is {0} mb)'.format(MAX_UPLOAD_SIZE/1000000))
        return picture
    

class AssemblyCodeForm(forms.ModelForm):
    timeout: int = forms.IntegerField(label='Max Timeout (seconds)', initial=30, required=False, max_value=120, min_value=1)
    class Meta:
        model = AssemblyCode
        exclude = ('file_prefix', 'code_text', 'state_file', 'creation_time', 'created_by')
        # widgets = { 'title': forms.CharField(max_length=200),
        #            'code_file': forms.FileInput(attrs={'id':'id_code_file'})}
        labels = {'title': "File Title", 'code_file': "Upload C File", 'timeout': "Max Timeout (seconds)"}
        
    def clean_code_file(self):
        
        code_file = self.cleaned_data['code_file']
        if not code_file:
            return code_file
        if not hasattr(code_file, 'content_type'):
            raise forms.ValidationError('You must upload a c code file')
        # if not code_file.content_type or not code_file.content_type.startswith('image'):
        #     raise forms.ValidationError('File type is not image')
        if code_file.size > MAX_UPLOAD_SIZE:
            raise forms.ValidationError('File too big (max size is {0} mb)'.format(MAX_UPLOAD_SIZE/1000000))
        return code_file
    
