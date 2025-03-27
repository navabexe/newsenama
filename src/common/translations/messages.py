# 📄 common/translations/messages.py

MESSAGES = {
    "otp.invalid": {
        "fa": "کد تایید اشتباه است.",
        "en": "The OTP code is incorrect."
    },
    "otp.expired": {
        "fa": "کد تایید منقضی شده است.",
        "en": "The OTP code has expired."
    },
    "auth.login.success": {
        "fa": "ورود با موفقیت انجام شد.",
        "en": "Login successful."
    },
    "auth.profile.incomplete": {
        "fa": "لطفاً پروفایل خود را تکمیل کنید.",
        "en": "Please complete your profile."
    },
    "auth.profile.completed": {
        "fa": "پروفایل با موفقیت تکمیل شد.",
        "en": "Profile completed successfully."
    },
    "auth.profile.pending": {
        "fa": "پروفایل در انتظار تایید ادمین است.",
        "en": "Profile is pending admin approval."
    },
    "token.invalid": {
        "fa": "توکن نامعتبر است.",
        "en": "Invalid token."
    },
    "token.expired": {
        "fa": "توکن منقضی شده است.",
        "en": "Token has expired."
    },
    "user.not_found": {
        "fa": "کاربر یافت نشد.",
        "en": "User not found."
    },
    "vendor.not_eligible": {
        "fa": "فروشنده مجاز به تکمیل پروفایل نیست.",
        "en": "Vendor is not eligible for profile completion."
    },
    "server.error": {
        "fa": "خطای داخلی سرور.",
        "en": "Internal server error."
    },
    "otp.sent": {
        "fa": "کد تایید برای شما ارسال شد.",
        "en": "OTP has been sent to your phone."
    },
    "otp.too_many.1min": {
        "fa": "تعداد درخواست در یک دقیقه زیاد است.",
        "en": "Too many OTP requests in 1 minute."
    },
    "otp.too_many.10min": {
        "fa": "تعداد درخواست در ۱۰ دقیقه زیاد است.",
        "en": "Too many OTP requests in 10 minutes."
    },
    "otp.too_many.blocked": {
        "fa": "به دلیل تعداد بالای درخواست، موقتاً مسدود شده‌اید.",
        "en": "You are temporarily blocked due to too many requests."
    },
    "auth.logout.single": {
        "fa": "شما با موفقیت از این نشست خارج شدید.",
        "en": "You have been logged out from this session."
    },
    "auth.logout.all": {
        "fa": "شما از تمام نشست‌ها خارج شدید.",
        "en": "You have been logged out from all sessions."
    },
    "auth.forbidden": {
        "fa": "دسترسی غیرمجاز.",
        "en": "Access denied."
    },
    "auth.force_logout.success": {
        "fa": "کاربر با موفقیت از تمام نشست‌ها خارج شد.",
        "en": "User successfully logged out from all sessions."
    },
    "account.deletion.requested": {
        "fa": "درخواست حذف حساب شما ثبت شد. تیم پشتیبانی به زودی بررسی خواهد کرد.",
        "en": "Your account deletion request has been submitted. Support will review it soon."
    },
    "token.refreshed": {
        "fa": "توکن‌ها با موفقیت به‌روزرسانی شدند.",
        "en": "Tokens refreshed successfully."
    }

}


def get_message(key: str, lang: str = "fa") -> str:
    """
    Retrieve a localized message based on key and language.

    Args:
        key (str): Message key (e.g., 'otp.invalid')
        lang (str): Language code ('fa' or 'en')

    Returns:
        str: Localized message or key as fallback
    """
    return MESSAGES.get(key, {}).get(lang) or MESSAGES.get(key, {}).get("en") or key
