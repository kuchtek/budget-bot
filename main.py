import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackContext,
    CallbackQueryHandler,
)
from datetime import datetime
import os
from pyairtable import Api

# Notion API configuration
NOTION_API_TOKEN = os.environ["NOTION_API_TOKEN"]
NOTION_EXPENSES_DATABASE_ID = "e01498b500854922bde3d422ee7c5ecd"
NOTION_BUDGET_DATABASE_ID = "27197324ba6043ad83c9529741de465e"
AIRTABLE_BASE_ID = os.environ["AIRTABLE_BASE_ID"]
AIRTABLE_API_KEY = os.environ["AIRTABLE_TOKEN"]
AIRTABLE_EXPENSES_TABLE = "Expenses"
AIRTABLE_BUDGET_TABLE = "BudgetData"

AIRTABLE_API_URL = f"https://api.airtable.com/v0/{AIRTABLE_BASE_ID}"

headers = {
    "Authorization": f"Bearer {AIRTABLE_API_KEY}",
    "Content-Type": "application/json",
}
api = Api(AIRTABLE_API_KEY)


def add_expense_airtable(date, category, account, amount, description):
    add_expense_to_airtable(date, category, account, amount, description)
    month = date[:7]
    budget = get_budget_from_airtable(category, month)
    update_budget_in_airtable(budget["id"], budget["fields"]["Remaining"] - amount)


def add_expense_to_airtable(date, category, account, amount, description):
    url = f"{AIRTABLE_API_URL}/{AIRTABLE_EXPENSES_TABLE}"
    data = {
        "fields": {
            "Date": date,
            "Category": category,
            "Account": account,
            "Amount": amount,
            "Description": description,
        }
    }

    response = requests.post(url, headers=headers, json=data)
    return response.status_code, response.json()


def get_budget_from_airtable(category, month):
    url = f"{AIRTABLE_API_URL}/{AIRTABLE_BUDGET_TABLE}"
    params = {"filterByFormula": f"AND(Category='{category}', Month='{month}')"}
    response = requests.get(url, headers=headers, params=params)
    if response.status_code == 200:
        records = response.json().get("records", [])
        if records:
            return records[0]
    return None


def update_budget_in_airtable(record_id, remaining_budget):
    url = f"{AIRTABLE_API_URL}/{AIRTABLE_BUDGET_TABLE}/{record_id}"
    data = {"fields": {"Remaining": remaining_budget}}
    response = requests.patch(url, headers=headers, json=data)
    return response.status_code, response.json()


def add_budget_to_airtable(category, budget, month):
    url = f"{AIRTABLE_API_URL}/{AIRTABLE_BUDGET_TABLE}"
    data = {
        "fields": {
            "Category": category,
            "Month": month,
            "Budget": budget,
            "Remaining": budget,
        }
    }
    response = requests.post(url, headers=headers, json=data)
    return response.status_code, response.json()


def check_category_exists(category):
    url = f"https://api.notion.com/v1/databases/{NOTION_BUDGET_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {"filter": {"property": "Kategoria", "title": {"equals": category}}}
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        results = response.json().get("results", [])
        return len(results) > 0
    return False


def add_category_to_notion(category):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "parent": {"database_id": NOTION_BUDGET_DATABASE_ID},
        "properties": {"Kategoria": {"title": [{"text": {"content": category}}]}},
    }
    response = requests.post(url, json=data, headers=headers)
    return response.status_code, response.json()


def get_categories_from_notion():
    url = f"https://api.notion.com/v1/databases/{NOTION_BUDGET_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    response = requests.post(url, headers=headers)
    if response.status_code == 200:
        results = response.json().get("results", [])
        categories = [
            entry["properties"]["Kategoria"]["title"][0]["text"]["content"]
            for entry in results
        ]
        return list(set(categories))  # Unikalne kategorie
    return []


async def add_category(update: Update, context: CallbackContext) -> None:
    try:
        # Oczekiwany format: /addcategory KATEGORIA
        text = update.message.text.split(maxsplit=1)
        if len(text) < 2:
            await update.message.reply_text(
                "Błędny format. Użyj: /addcategory KATEGORIA"
            )
            return

        category = text[1]

        # Sprawdź, czy kategoria już istnieje
        if check_category_exists(category):
            await update.message.reply_text(f'Kategoria "{category}" już istnieje.')
            return

        # Dodaj kategorię do Notion
        status_code, response = add_category_to_notion(category)
        if status_code != 200:
            await update.message.reply_text(
                f"Wystąpił błąd podczas dodawania kategorii do Notion: {response}"
            )
            return

        await update.message.reply_text(f"Dodano nową kategorię: {category}")
    except Exception as e:
        await update.message.reply_text(f"Wystąpił błąd: {e}")


# Funkcja do wylistowania kategorii
async def get_categories(update: Update, context: CallbackContext) -> None:
    try:
        categories = get_categories_from_notion()
        if categories:
            categories_message = "Dostępne kategorie:\n" + "\n".join(categories)
        else:
            categories_message = "Nie znaleziono żadnych kategorii."
        await update.message.reply_text(categories_message)
    except Exception as e:
        await update.message.reply_text(f"Wystąpił błąd: {e}")


def get_budget_from_notion(category, month):
    url = f"https://api.notion.com/v1/databases/{NOTION_BUDGET_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "filter": {
            "and": [
                {"property": "Kategoria", "title": {"equals": category}},
                {"property": "Miesiąc", "date": {"equals": month}},
            ]
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            return results[0]
    return None


# Funkcja do dodawania budżetu do Notion
def add_budget_to_notion(category, budget, month):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "parent": {"database_id": NOTION_BUDGET_DATABASE_ID},
        "properties": {
            "Kategoria": {"title": [{"text": {"content": category}}]},
            "Miesiąc": {"date": {"start": month}},
            "Budżet": {"number": budget},
            "Pozostało": {"number": budget},
        },
    }
    response = requests.post(url, json=data, headers=headers)
    return response.status_code, response.json()


def update_budget_in_notion(category, month, amount):
    url = f"https://api.notion.com/v1/databases/{NOTION_BUDGET_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "filter": {
            "and": [
                {"property": "Kategoria", "title": {"equals": category}},
                {"property": "Miesiąc", "date": {"equals": month + "-01"}},
            ]
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            page_id = results[0]["id"]
            current_remaining = results[0]["properties"]["Pozostało"]["number"]
            new_remaining = current_remaining - amount

            url = f"https://api.notion.com/v1/pages/{page_id}"
            data = {"properties": {"Pozostało": {"number": new_remaining}}}
            response = requests.patch(url, json=data, headers=headers)
            return response.status_code, response.json()
    return response.status_code, response.json()


# Funkcja do dodawania wydatków do Notion
def add_expense_to_notion(date, category, account, expense, description):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "parent": {"database_id": NOTION_EXPENSES_DATABASE_ID},
        "properties": {
            "Data": {"date": {"start": date}},
            "Kategoria": {"title": [{"text": {"content": category}}]},
            "Konto": {"rich_text": [{"text": {"content": account}}]},
            "Wydatek": {"number": expense},
            "Opis": {"rich_text": [{"text": {"content": description}}]},
        },
    }
    response = requests.post(url, json=data, headers=headers)
    return response.status_code, response.json()


# Funkcja, która obsługuje komendę /start
async def start(update: Update, context: CallbackContext) -> None:
    start_message = (
        "Cześć! Jestem Twoim botem budżetowym. Oto dostępne komendy:\n\n"
        "/add KATEGORIA KONTO WYDATEK OPIS - Dodaj wydatek. Przykład: /add Jedzenie Konto1 50.00 Obiad\n"
        "/setbudget KATEGORIA BUDŻET MIESIĄC - Ustaw budżet na kategorię. Przykład: /setbudget Jedzenie 1000 2024-06\n"
        "/getcategories - Wyświetl dostępne kategorie.\n"
        "/addcategory KATEGORIA - Dodaj nową kategorię.\n\n"
        "Uwaga: Wszystkie kwoty są w PLN. Wydatki i budżety są skorelowane z interwałem miesięcznym."
        "Wydaj mi komendę a ja będę działać.."
    )
    await update.message.reply_text(start_message)


async def set_budget(update: Update, context: CallbackContext) -> None:
    categories = get_categories_from_notion()
    if not categories:
        await update.message.reply_text("Nie znaleziono żadnych kategorii.")
        return

    keyboard = [
        [
            InlineKeyboardButton(category, callback_data=f"setbudget_{category}")
            for category in categories
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Wybierz kategorię:", reply_markup=reply_markup)


async def set_budget_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    category = query.data.split("_")[1]
    context.user_data["selected_category"] = category
    await query.edit_message_text(
        text=f"Wybrana kategoria: {category}. Podaj kwotę budżetu i miesiąc w formacie BUDŻET YYYY-MM (brak daty=aktualny miesiąc) "
    )


async def handle_expense_input(update: Update, context: CallbackContext) -> None:
    try:
        text = update.message.text.split(maxsplit=3)
        if len(text) < 4:
            await update.message.reply_text(
                "Błędny format. Użyj: WYDATEK KWOTA KATEGORIA OPIS"
            )
            return

        amount = float(text[1])
        category = text[2]
        description = text[3]

        # Dodaj wydatek do Notion
        status_code, response = add_expense_to_notion(category, amount, description)
        if status_code != 200:
            await update.message.reply_text(
                f"Wystąpił błąd podczas dodawania wydatku do Notion: {response}"
            )
            return

        await update.message.reply_text(
            f"Dodano wydatek: {amount} {category} - {description}"
        )
    except Exception as e:
        await update.message.reply_text(f"Wystąpił błąd: {e}")


async def choose_category(update: Update, context: CallbackContext) -> None:
    categories = get_categories_from_notion()
    keyboard = [
        [InlineKeyboardButton(category, callback_data=category)]
        for category in categories
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Wybierz kategorię:", reply_markup=reply_markup)


# Funkcja obsługi callback dla wyboru kategorii
async def handle_category_choice(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    category = query.data

    context.user_data["selected_category"] = category
    await query.message.reply_text(f"Wybrano kategorię: {category}")
    await query.message.delete_reply_markup()  # Usuń klawiaturę wyboru kategorii


async def handle_budget_input(update: Update, context: CallbackContext) -> None:
    try:
        if "selected_category" not in context.user_data:
            await update.message.reply_text(
                "Najpierw wybierz kategorię używając /setbudget."
            )
            return

        text = update.message.text.split(maxsplit=2)
        month = ""
        if len(text) < 2:
            month = datetime.now().strftime("%Y-%m")
            # await update.message.reply_text('Błędny format. Użyj: BUDŻET YYYY-MM')
            # return
        else:
            month = text[1]
        budget = float(text[0])

        # Uzupełnij datę o pierwszy dzień danego miesiąca
        if "-" in month:
            year, month = month.split("-")
            month = f"{year}-{month}-01"

        category = context.user_data["selected_category"]

        # Sprawdź, czy budżet dla danej kategorii i miesiąca już istnieje
        existing_budget = get_existing_budget_from_notion(category, month)
        if existing_budget:
            keyboard = [
                [InlineKeyboardButton("Tak", callback_data="yes")],
                [InlineKeyboardButton("Nie", callback_data="no")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                f"Istnieje już budżet dla kategorii {category} na miesiąc {month} w wysokości {existing_budget}. Czy chcesz go nadpisać?",
                reply_markup=reply_markup,
            )
            context.user_data["existing_budget"] = existing_budget
            context.user_data["budget_month"] = month
            return

        # Dodaj budżet do Notion
        status_code, response = add_budget_to_notion(category, budget, month)
        if status_code != 200:
            await update.message.reply_text(
                f"Wystąpił błąd podczas dodawania budżetu do Notion: {response}"
            )
            return

        await update.message.reply_text(
            f"Ustawiono budżet dla kategorii {category} na miesiąc {month} w wysokości {budget}"
        )
        del context.user_data["selected_category"]
    except Exception as e:
        await update.message.reply_text(f"Wystąpił błąd: {e}")


# Funkcja obsługi callback dla przycisków "Tak" i "Nie"
async def handle_budget_confirmation(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    choice = query.data

    if choice == "yes":
        existing_budget = context.user_data.get("existing_budget")
        budget_month = context.user_data.get("budget_month")
        # Nadpisz istniejący budżet
        # add_budget_to_notion(category, existing_budget, budget_month) - dodaj implementację nadpisywania budżetu
        await query.message.reply_text(
            f"Nadpisano istniejący budżet dla miesiąca {budget_month} w wysokości {existing_budget}."
        )
    elif choice == "no":
        await query.message.reply_text("Nie nadpisano istniejącego budżetu.")


# Rejestracja funkcji obsługi callback


def get_existing_budget_from_notion(category, month):
    url = f"https://api.notion.com/v1/databases/{NOTION_BUDGET_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }
    data = {
        "filter": {
            "and": [
                {"property": "Kategoria", "title": {"equals": category}},
                {"property": "Miesiąc", "date": {"equals": month}},
            ]
        }
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code == 200:
        results = response.json().get("results", [])
        if results:
            return results[0]["properties"]["Budżet"]["number"]
    return None


async def add_expense(update: Update, context: CallbackContext) -> None:
    try:
        # Oczekiwany format: /add KATEGORIA KONTO WYDATEK OPIS
        text = update.message.text.split(maxsplit=4)
        if len(text) < 5:
            await update.message.reply_text(
                "Błędny format. Użyj: /add KATEGORIA KONTO WYDATEK OPIS"
            )
            return

        category, account, amount, description = (
            text[1],
            text[2],
            float(text[3]),
            text[4],
        )
        current_date = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")  # Extracting YYYY-MM

        # Dodaj wydatek do Notion
        status_code, response = add_expense_to_notion(
            current_date, category, account, amount, description
        )
        if status_code != 200:
            await update.message.reply_text(
                f"Wystąpił błąd podczas dodawania wydatku do Notion: {response}"
            )
            return

        # Zaktualizuj budżet w Notion
        status_code, response = update_budget_in_notion(category, month, amount)
        if status_code != 200:
            await update.message.reply_text(
                f"Wystąpił błąd podczas aktualizacji budżetu w Notion: {response}"
            )
            return

        await update.message.reply_text(
            f'Dodano wydatek: {category} {account} {amount} {description}. Pozostało: {response["properties"]["Pozostało"]["number"]} PLN.'
        )
    except Exception as e:
        await update.message.reply_text(f"Wystąpił błąd: {e}")


# Funkcja, która obsługuje zwykłe wiadomości tekstowe
async def echo(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(update.message.text)


def main() -> None:
    # # Stwórz application i przekaz mu token API bota
    token = os.environ["TELEGRAM_TOKEN"]
    application = Application.builder().token(token).build()

    # Zarejestruj handler dla komendy /start
    application.add_handler(CommandHandler("start", start))

    # Zarejestruj handler dla komendy /getcategories
    application.add_handler(CommandHandler("getcategories", get_categories))

    # Zarejestruj handler dla komendy /setbudget
    application.add_handler(CommandHandler("setbudget", set_budget))

    # Zarejestruj handler dla odpowiedzi z Inline Keyboard
    application.add_handler(
        CallbackQueryHandler(set_budget_callback, pattern="^setbudget_")
    )

    # Zarejestruj handler dla komendy /addcategory
    application.add_handler(CommandHandler("addcategory", add_category))

    # Zarejestruj handler dla komendy /add
    application.add_handler(CommandHandler("add", add_expense))

    # Zarejestruj handler dla budżetu po wyborze kategorii
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_budget_input)
    )

    # Zarejestruj handler, który odbiera wszystkie wiadomości tekstowe i wysyła je z powrotem (echo)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    application.add_handler(CallbackQueryHandler(handle_budget_confirmation))
    # Rejestracja funkcji obsługi callback dla wyboru kategorii
    application.add_handler(CallbackQueryHandler(handle_category_choice))
    # Uruchom bota
    print("Bot ready to receive requests!")
    application.run_polling()


if __name__ == "__main__":
    # Dodaj wydatek
    date = "2024-05-29"
    category = "Jedzenie"
    account = "Konto1"
    amount = 50.00
    description = "Obiad"
    add_expense_airtable(date, category, account, amount, description)
    main()
