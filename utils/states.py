# utils/states.py
from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    lang_selection = State() # For initial language selection
    channel_link_input = State() # For initial channel setup

    # Boosting orders
    boosting_choose_type = State()
    boosting_choose_channel = State()
    boosting_enter_subscribers = State()
    boosting_confirm_order = State()

    # Promocodes
    input_promocode = State()

    # Admin panel
    admin_broadcast = State()
    admin_add_promo_name = State()
    admin_add_promo_credits = State()
    admin_add_promo_activations = State()
    admin_add_promo_expires = State()
    admin_add_promo_ip_serial = State()
    admin_ban_user_id = State()
    admin_set_balance_id = State()
    admin_set_slots_id = State()
    admin_check_user_id = State()