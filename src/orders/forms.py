from django import forms

class CheckoutForm(forms.Form):
    customer_name = forms.CharField(max_length=140, label="Имя и фамилия")
    email = forms.EmailField(label="Email")
    phone = forms.CharField(max_length=40, label="Телефон")
    shipping_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), label="Адрес доставки")
    billing_same = forms.BooleanField(required=False, initial=True, label="Платёжный адрес совпадает")
    billing_address = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), required=False, label="Платёжный адрес")
    promo_code = forms.CharField(max_length=32, required=False, label="Промокод")
