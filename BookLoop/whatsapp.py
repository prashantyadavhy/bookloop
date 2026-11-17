"""Open prepared BookLoop messages using WhatsApp Click-to-Chat."""

import urllib.parse
import webbrowser


def clean_phone_number(phone):
    """Keep digits and common phone formatting, then validate the number."""
    phone = phone.strip()
    phone_digits = ""

    for position in range(len(phone)):
        character = phone[position]
        if character.isdigit():
            phone_digits = phone_digits + character
        elif character == "+" and position == 0:
            # The plus sign is allowed only at the beginning of an international number.
            pass
        elif character == " " or character == "-":
            # These characters are allowed while typing, but not in wa.me URLs.
            pass
        elif character == "(" or character == ")":
            # Parentheses are also allowed as display formatting.
            pass
        else:
            return ""

    # WhatsApp Click-to-Chat expects digits with the country code included.
    if len(phone_digits) < 10 or len(phone_digits) > 15:
        return ""

    return phone_digits


def make_whatsapp_url(phone, message):
    """Build a Click-to-Chat URL, or return an empty string if invalid."""
    phone_digits = clean_phone_number(phone)

    if phone_digits == "":
        return ""

    encoded_message = urllib.parse.quote(message)
    whatsapp_url = "https://wa.me/" + phone_digits
    whatsapp_url = whatsapp_url + "?text=" + encoded_message
    return whatsapp_url


def send_whatsapp(phone, message):
    """Open WhatsApp with a prepared message; the user still presses Send."""
    whatsapp_url = make_whatsapp_url(phone, message)

    if whatsapp_url == "":
        print("The WhatsApp number is not valid.")
        return False

    browser_opened = webbrowser.open(whatsapp_url)
    return browser_opened


def send_request_message(owner_phone, book_name):
    """Prepare the message shown to the owner of a requested book."""
    message = "Hello! A student has requested your book on BookLoop.\n\n"
    message = message + "Book: " + book_name + "\n\n"
    message = message + "Please log in to BookLoop to accept or reject this request."
    return send_whatsapp(owner_phone, message)


def send_acceptance_message(requester_phone, book_name):
    """Prepare the message shown to a student whose request was accepted."""
    message = "Hello! Your book request on BookLoop has been accepted.\n\n"
    message = message + "Book: " + book_name + "\n\n"
    message = message + "Let's discuss a convenient time and place to exchange the book."
    return send_whatsapp(requester_phone, message)


def send_rejection_message(requester_phone, book_name):
    """Prepare the message shown to a student whose request was rejected."""
    message = "Hello! Unfortunately, your request for " + book_name
    message = message + " on BookLoop has been rejected or the book is no longer available.\n\n"
    message = message + "Thank you for using BookLoop."
    return send_whatsapp(requester_phone, message)


def send_donation_enquiry(owner_phone, book_name):
    """Prepare an enquiry from an interested student to a book owner."""
    message = "Hello! I found your free donation listing on BookLoop.\n\n"
    message = message + "Book: " + book_name + "\n\n"
    message = message + "I am interested in receiving this book. Is it still available?"
    return send_whatsapp(owner_phone, message)


def send_exchange_coordination(owner_phone, book_name):
    """Prepare a message to arrange an accepted book exchange."""
    message = "Hello! I would like to coordinate our BookLoop book exchange.\n\n"
    message = message + "Book: " + book_name + "\n\n"
    message = message + "Please let me know a convenient time and place."
    return send_whatsapp(owner_phone, message)
