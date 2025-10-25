from django import template

register = template.Library()

@register.filter
def add_class(field, css):
    """Добавляет CSS-класс к полю формы в шаблоне."""
    return field.as_widget(attrs={
        **field.field.widget.attrs,
        "class": (field.field.widget.attrs.get("class", "") + " " + css).strip()
    })
