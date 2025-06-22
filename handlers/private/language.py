# handlers/private/language.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from typing import Callable

from database.models import User # For type hinting User
from services.user_service import UserService
from utils.keyboards import get_main_menu_kb
from utils.callbacks import LanguageCallback
from utils.states import Form
import logging

logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(LanguageCallback.filter(), Form.lang_selection)
async def select_language(call: CallbackQuery, callback_data: LanguageCallback, state: FSMContext, user: User, user_service: UserService, _: Callable[[str], str]):
    lang_code = callback_data.lang_code
    
    if await user_service.update_user_language(user.id, lang_code):
        user.lang_code = lang_code # Update in-memory user object
        
        # Reload translation function for the current language immediately
        _ = await data["i18n"].set_locale(lang_code)

        await call.message.edit_text(_("language_selection.selected"))
        
        # Proceed with initial setup (channel link) or main menu
        if not user.channels:
            await call.message.answer(_("initial_channel_setup.prompt"))
            await state.set_state(Form.channel_link_input)
        else:
            await call.message.answer(_("main_menu.greeting").format(user_name=user.first_name or user.username), reply_markup=get_main_menu_kb(_))
            await state.clear() # Language set, initial setup done

    else:
        await call.message.edit_text(_("error.default"))
    
    await call.answer()