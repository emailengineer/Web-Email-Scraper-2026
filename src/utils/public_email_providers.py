"""List of public email providers for email validation."""

# Comprehensive list of public email providers
PUBLIC_EMAIL_PROVIDERS = {
    # Major providers
    'gmail.com',
    'yahoo.com',
    'hotmail.com',
    'outlook.com',
    'aol.com',
    'icloud.com',
    'mail.com',
    'protonmail.com',
    'proton.me',
    'yandex.com',
    'zoho.com',
    'gmx.com',
    'live.com',
    'msn.com',
    'me.com',
    'mac.com',
    'inbox.com',
    'fastmail.com',
    'tutanota.com',
    'mail.ru',
    'qq.com',
    '163.com',
    'sina.com',
    'rediffmail.com',
    'cox.net',
    'sbcglobal.net',
    'att.net',
    'bellsouth.net',
    'charter.net',
    'comcast.net',
    'earthlink.net',
    'juno.com',
    'netzero.net',
    'rocketmail.com',
    'ymail.com',
    'aim.com',
    'bigpond.com',
    'optusnet.com.au',
    'tpg.com.au',
    'iinet.net.au',
    'orange.fr',
    'laposte.net',
    'web.de',
    'gmx.de',
    't-online.de',
    'libero.it',
    'alice.it',
    'virgilio.it',
    'tiscali.it',
    'uol.com.br',
    'bol.com.br',
    'terra.com.br',
    'ig.com.br',
    'naver.com',
    'daum.net',
    'hanmail.net',
    'mailinator.com',
    'guerrillamail.com',
    '10minutemail.com',
    'tempmail.com',
    'throwaway.email',
    'disposable.email',
    'temp-mail.org',
    'getnada.com',
    'mohmal.com',
    'fakeinbox.com',
    'mintemail.com',
    'spamgourmet.com',
    'sharklasers.com',
    'grr.la',
    'guerrillamailblock.com',
    'pokemail.net',
    'spam4.me',
    'bccto.me',
    'chitthi.in',
    'meltmail.com',
    'emailondeck.com',
    'spamhole.com',
    'spamevader.com',
    'spamfree24.org',
    'tempinbox.co.uk',
    'mytrashmail.com',
    'trashmail.com',
    'trashmail.net',
    'jetable.org',
    'meltmail.com',
    'emailias.com',
    'mox.do',
    'yopmail.com',
    'emaildrop.io',
    'maildrop.cc',
    'getairmail.com',
    'mailcatch.com',
    'inboxkitten.com',
    'mailnesia.com',
    'mohmal.com',
    'tempr.email',
    'throwaway.email',
    'tmpmail.org',
    'mail7.io',
    'fakemailgenerator.com',
    'mailinator.com',
    'mailcatch.com',
    'getnada.com',
    'mintemail.com',
    'throwawaymail.com',
    'tempmailo.com',
    'mail-temp.com',
    'temp-mail.io',
    'mail-temp.com',
    'tempmailaddress.com',
    'mail-temp.com',
    'tempail.com',
    'mohmal.com',
    'throwaway.email',
    'maildrop.cc',
    'getnada.com',
    'mintemail.com',
    'throwawaymail.com',
    'tempmailo.com',
    'mail-temp.com',
    'temp-mail.io',
    'mail-temp.com',
    'tempmailaddress.com',
    'mail-temp.com',
    'tempail.com',
}

# Normalize all providers to lowercase for comparison
PUBLIC_EMAIL_PROVIDERS = {provider.lower() for provider in PUBLIC_EMAIL_PROVIDERS}


def is_public_email_provider(domain: str) -> bool:
    """
    Check if a domain is a public email provider.
    
    Args:
        domain: Email domain to check
        
    Returns:
        True if domain is a known public email provider
    """
    return domain.lower() in PUBLIC_EMAIL_PROVIDERS


def is_valid_email_domain(email_domain: str, target_domain: str) -> bool:
    """
    Check if an email domain is valid (target domain or public provider).
    
    Args:
        email_domain: Domain from email address
        target_domain: Target domain being scraped
        
    Returns:
        True if email domain is target domain or public provider
    """
    email_domain_lower = email_domain.lower()
    target_domain_lower = target_domain.lower()
    
    # Accept target domain
    if email_domain_lower == target_domain_lower:
        return True
    
    # Accept public email providers
    if is_public_email_provider(email_domain_lower):
        return True
    
    return False

