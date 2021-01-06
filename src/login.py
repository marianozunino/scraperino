import requests
from bs4 import BeautifulSoup

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
    "Referer": "https://establecimientos.prismamediosdepago.com/establecimientos/login",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


def do_login(cuit=None, password=None):
    session = requests.Session()

    response = session.get(
        "https://establecimientos.prismamediosdepago.com/establecimientos/login",
        headers=headers,
    )

    soup = BeautifulSoup(response.text, "html.parser")

    try:
        jsf_view_state = soup.find("input", {"id": "javax.faces.ViewState"}).get(
            "value"
        )
    except Exception:
        raise Exception("is Prisma down?")

    data = {
        "loginFrm": "loginFrm",
        "loginFrm:docType": "CUIT",
        "loginFrm:username": "30-51586616-3",  # TODO hardcoded cuit
        "loginFrm:password": "lore2020",  # TODO hardcoded password
        "loginFrm:button:button": "Ingresar",
        "javax.faces.ViewState": jsf_view_state,
    }

    response = session.post(
        "https://establecimientos.prismamediosdepago.com/establecimientos/login",
        headers=headers,
        data=data,
    )
    soup = BeautifulSoup(response.text, "html.parser")

    error_tag = soup.find("span", {"class": "login-error"})
    if error_tag is not None:
        raise Exception("Login failed")
    return session
