# i18n/__init__.py

from aiogram_i18n.middleware import I18nMiddleware

i18n_manager = I18nMiddleware(
    path="i18n/locales",  # или './i18n/locales', если путь от корня проекта
    default_locale="ru",
    use_locale_path=True
)
