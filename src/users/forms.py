from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()


class ProfileForm(forms.ModelForm):
    phone = forms.CharField(
        required=False,
        label="Телефон",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "+995 ..."})
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "input"}),
            "last_name": forms.TextInput(attrs={"class": "input"}),
            "email": forms.EmailInput(attrs={"class": "input"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # Если пользователь уже есть — подставляем его данные
        if self.user:
            self.fields["first_name"].initial = self.user.first_name
            self.fields["last_name"].initial = self.user.last_name
            self.fields["email"].initial = self.user.email
            # Если в модели User нет phone — можно подключить user.profile.phone
            if hasattr(self.user, "profile"):
                self.fields["phone"].initial = getattr(self.user.profile, "phone", "")

    def save(self, commit=True):
        user = self.user
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        if hasattr(user, "profile"):
            user.profile.phone = self.cleaned_data["phone"]
            user.profile.save()
        return user
