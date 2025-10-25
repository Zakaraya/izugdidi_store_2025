from django import forms
from .models import Order

class CheckoutForm(forms.ModelForm):
    shipping_address = forms.CharField(
        required=False, label="Адрес доставки",
        widget=forms.Textarea(attrs={"class": "input", "rows": 3, "placeholder": "Город, улица, дом, квартира/офис"})
    )
    billing_same = forms.BooleanField(
        required=False, initial=True, label="Платёжный адрес совпадает с адресом доставки"
    )
    billing_address = forms.CharField(
        required=False, label="Платёжный адрес",
        widget=forms.Textarea(attrs={"class": "input", "rows": 3, "placeholder": "Город, улица, дом, квартира/офис"})
    )
    promo_code = forms.CharField(
        required=False, label="Промокод",
        widget=forms.TextInput(attrs={"class": "input", "placeholder": "Промокод"})
    )

    class Meta:
        model = Order
        fields = ["delivery_method", "customer_name", "email", "phone"]
        widgets = {
            "delivery_method": forms.Select(attrs={"class": "input"}),
            "customer_name": forms.TextInput(attrs={"class": "input", "placeholder": "Имя и фамилия"}),
            "email": forms.EmailInput(attrs={"class": "input", "placeholder": "email@example.com"}),
            "phone": forms.TextInput(attrs={"class": "input", "placeholder": "+995 ..."}),
        }

    def clean(self):
        data = super().clean()
        method = data.get("delivery_method") or Order.DELIVERY_PICKUP
        shipping_address = self.cleaned_data.get("shipping_address", "").strip()
        billing_same = bool(self.cleaned_data.get("billing_same"))
        billing_address = self.cleaned_data.get("billing_address", "").strip()

        if method == Order.DELIVERY_ADDRESS:
            if not shipping_address:
                self.add_error("shipping_address", "Обязательное поле для доставки")

        if not billing_same:
            if not billing_address:
                self.add_error("billing_address", "Укажите платёжный адрес или отметьте совпадение")

        return data

    def _build_address(self, kind: str):
        """
        kind: 'shipping' | 'billing'
        Возвращает словарь для JSON-поля, либо {} если не нужно.
        """
        method = self.cleaned_data.get("delivery_method")
        if kind == "shipping":
            if method == Order.DELIVERY_ADDRESS:
                return {
                    "method": "address",
                    "text": (self.cleaned_data.get("shipping_address") or "").strip(),
                }
            return {"method": "pickup", "store": "Zugdidi shop"}
        # billing
        if self.cleaned_data.get("billing_same"):
            # копию соберём в save(), чтобы точно соответствовать shipping
            return {}  # маркёр: возьмём потом из shipping
        return {
            "text": (self.cleaned_data.get("billing_address") or "").strip()
        }

    def save(self, commit=True):
        order = super().save(commit=False)
        shipping_json = self._build_address("shipping")
        billing_json = self._build_address("billing")
        if not billing_json:
            # копируем из shipping, если billing_same = True
            billing_json = dict(shipping_json)
            # но укажем тип, что это billing-копия (по желанию)
            billing_json["as"] = "billing_same"
        order.shipping_address_json = shipping_json
        order.billing_address_json = billing_json
        if commit:
            order.save()
        return order
