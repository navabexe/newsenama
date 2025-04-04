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
    "auth.login.missing_credentials": {
        "fa": "شماره تلفن یا نام کاربری لازم است.",
        "en": "Phone or username is required."
    },
    "auth.login.too_many_credentials": {
        "fa": "فقط یکی از شماره تلفن یا نام کاربری را وارد کنید.",
        "en": "Provide either phone or username, not both."
    },
    "auth.login.invalid": {
        "fa": "اطلاعات ورود نامعتبر است.",
        "en": "Invalid credentials."
    },
    "auth.login.no_password": {
        "fa": "رمز عبور برای این حساب تنظیم نشده است.",
        "en": "Password not set."
    },
    "auth.login.not_active": {
        "fa": "حساب فعال نیست.",
        "en": "Account not active."
    },
    "auth.login.too_many_attempts": {
        "fa": "تعداد تلاش‌های ورود بیش از حد است. لطفاً بعداً تلاش کنید.",
        "en": "Too many login attempts. Please try again later."
    },
    "token.invalid": {
        "fa": "توکن نامعتبر است.",
        "en": "Invalid token."
    },
    "token.expired": {
        "fa": "توکن منقضی شده است.",
        "en": "Token has expired."
    },
    "token.refreshed": {
        "fa": "توکن‌ها با موفقیت به‌روزرسانی شدند.",
        "en": "Tokens refreshed successfully."
    },
    "user.not_found": {
        "fa": "کاربر یافت نشد.",
        "en": "User not found."
    },
    "vendor.not_eligible": {
        "fa": "فروشنده مجاز به تکمیل پروفایل نیست.",
        "en": "Vendor is not eligible for profile completion."
    },
    "vendor.approved": {
        "fa": "پروفایل فروشنده شما تأیید شد!",
        "en": "Your vendor profile has been approved!"
    },
    "vendor.rejected": {
        "fa": "پروفایل فروشنده شما رد شد.",
        "en": "Your vendor profile was rejected."
    },
    "vendor.status_update.title": {
        "fa": "به‌روزرسانی وضعیت پروفایل",
        "en": "Profile Status Update"
    },
    "vendor.invalid_id": {
        "fa": "شناسه فروشنده نامعتبر است.",
        "en": "Invalid vendor ID format."
    },
    "vendor.not_pending": {
        "fa": "فروشنده در انتظار تأیید نیست.",
        "en": "Vendor is not pending approval."
    },
    "session.invalid": {
        "fa": "نوع سشن نامعتبر است.",
        "en": "Invalid session type."
    },
    "account.deletion.requested": {
        "fa": "درخواست حذف حساب شما ثبت شد. تیم پشتیبانی به زودی بررسی خواهد کرد.",
        "en": "Your account deletion request has been submitted. Support will review it soon."
    },
    "server.error": {
        "fa": "خطای سرور رخ داد.",
        "en": "Server error occurred."
    },
    "notification.otp_requested.title": {
        "fa": "درخواست کد تایید",
        "en": "OTP Requested"
    },
    "notification.otp_requested.body": {
        "fa": "کد تایید برای شماره {phone} با هدف {purpose} ارسال شد. کد: {otp}",
        "en": "OTP has been sent to {phone} for {purpose} purpose. Code: {otp}"
    },
    "notification.otp_verified.title": {
        "fa": "کد تایید تأیید شد",
        "en": "OTP Verified"
    },
    "notification.otp_verified.body": {
        "fa": "کد تایید برای شماره {phone} با موفقیت تأیید شد.",
        "en": "OTP for {phone} has been successfully verified."
    },
    # Title & body for successful user profile completion
    "notification.user.profile_completed.title": {
        "fa": "پروفایل شما با موفقیت تکمیل شد",
        "en": "Your profile has been successfully completed"
    },
    "notification.user.profile_completed.body": {
        "fa": "از اینکه اطلاعات خود را تکمیل کردید سپاسگزاریم.",
        "en": "Thank you for completing your profile."
    },

    # Title & body for vendor profile submission (pending approval)
    "notification.vendor.profile_pending.title": {
        "fa": "پروفایل در انتظار تایید",
        "en": "Vendor Profile Pending"
    },
    "notification.vendor.profile_pending.body": {
        "fa": "پروفایل فروشنده شما برای بررسی ارسال شد. منتظر تایید مدیر باشید.",
        "en": "Your vendor profile has been submitted for review. Please wait for admin approval."
    },
    "notification.admin.vendor_pending.title": {
        "fa": "درخواست فروشنده جدید",
        "en": "New Vendor Request"
    },
    "notification.admin.vendor_pending.body": {
        "fa": "یک فروشنده جدید منتظر تایید است: {name}",
        "en": "A new vendor is awaiting approval: {name}"
    },
    "otp.valid": {
        "fa": "کد تایید با موفقیت تأیید شد.",
        "en": "OTP has been successfully verified."
    },
    "notification.admin.vendor_submitted.body": {
        "fa": "فروشنده {vendor_name} با شماره {vendor_phone} پروفایل خود را برای بررسی ارسال کرده است.",
        "en": "Vendor {vendor_name} with phone number {vendor_phone} has submitted their profile for review."
    },
    "notification.admin.vendor_submitted.title": {
    "fa": "ارسال پروفایل فروشنده",
    "en": "Vendor Profile Submitted"
    },
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
