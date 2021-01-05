from typing import TypedDict
from bs4 import BeautifulSoup
import requests


class Account(TypedDict):
    id: str
    providerId: str
    name: str
    bankName: str
    # note: bankAccount is not available, only bank name.
    bankAccount: str
    state: str
    cardBrand: str
    position: int


def get_branches_and_accounts(session: requests.Session):
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
    response = session.get(
        "https://establecimientos.prismamediosdepago.com/establecimientos/app/landing",
        headers=headers,
    )

    soup = BeautifulSoup(response.text, "html.parser")
    options = soup.select(
        "#header\\:estabSelectorFrm\\:estab-dropdown-menu-select2\\:sel2 > option"
    )

    parsed_branches = []
    parsed_accounts = []

    for index, option in enumerate(options):
        option_parts = option.text.split("|")
        provider_id = option_parts[0].strip()
        parsed_branch = {
            "id": provider_id,
            "name": option_parts[2].strip(),
            "brandName": option_parts[2].strip(),
            "address": "",
            "state": option_parts[3].strip(),
        }
        parsed_account = Account(
            id=provider_id,
            providerId=provider_id,
            name=option_parts[2].strip(),
            bankName=option_parts[4].strip(),
            # note: bankAccount is not available, only bank name.
            bankAccount="",
            state=option_parts[3].strip(),
            cardBrand=map_credit_card(option_parts[5].strip()),
            position=index,
        )

        parsed_branches.append(parsed_branch)
        parsed_accounts.append(parsed_account)

    return parsed_branches, parsed_accounts


def map_credit_card(value: str) -> str:
    if value == "900":
        return "VISA"
    if value == "391":
        return "CABAL"
    return "MASTERCARD"
