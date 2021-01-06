import re
from datetime import datetime
from dateutil.parser import parse, parserinfo
from src.login_exception import LoginException
from typing import Union
from bs4 import BeautifulSoup
from bs4.element import ResultSet
import requests

from src.paymet_details import download_payment_xls

headers = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
}


class Payments:
    session: requests.Session = None
    accounts = None
    start_date: datetime = None
    end_date: datetime = None
    jsf_state: str = None
    current_account_id: str = None
    __PRISMA_PAYMENTS_XLS_MAX_DAYS_OLD = 60

    def __init__(
        self,
        session: requests.Session,
        accounts,
        start_date: datetime,
        end_date: datetime,
    ):
        self.session = session
        self.start_date = start_date
        self.end_date = end_date
        self.accounts = accounts
        self.get_payments()

    def get_payments(self):
        payments = []
        for account in self.accounts:
            self.change_account(account)
            print(f"~ daily report for account {self.current_account_id}")
            print("~ go to daily report ~")
            soup = self.goto_daily_report()
            rows, pages = self.extract_rows_and_pages(soup)

            if not pages:
                print(f" account {self.current_account_id} has not data \n")
                continue
            else:
                payments.extend(self.extract_payments_from_rows(rows))

            for _ in range(1, int(pages)):
                soup = self.next_page()
                rows, _ = self.extract_rows_and_pages(soup)
                payments.extend(self.extract_payments_from_rows(rows))
            print("\n")
        print(f"Fetched payments {len(payments)}")

    def goto_daily_report(self) -> BeautifulSoup:
        response = self.session.get(
            "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/resumenDiario",
            headers=headers,
        )
        soup = BeautifulSoup(response.text, "html.parser")
        jsf_view_state = soup.find("input", {"id": "javax.faces.ViewState"}).get(
            "value"
        )
        self.jsf_state = jsf_view_state
        return soup

    def change_account(self, account: dict[str, str]):
        self.current_account_id = account["id"]
        self.goto_daily_report()
        data = {
            "header:estabSelectorFrm": "header:estabSelectorFrm",
            "header:estabSelectorFrm:estab-dropdown-menu-select2:sel2": self.current_account_id,
            "header:estabSelectorFrm:selectedEstabHidden": self.current_account_id,
            "javax.faces.ViewState": self.jsf_state,
            "javax.faces.source": "header:estabSelectorFrm:estabSelected",
            "javax.faces.partial.event": "click",
            "javax.faces.partial.execute": "header:estabSelectorFrm:estabSelected header:estabSelectorFrm:userInfo",
            "javax.faces.partial.render": "@all",
            "javax.faces.behavior.event": "action",
            "javax.faces.partial.ajax": "true",
        }

        self.session.post(
            "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/resumenDiario",
            headers=headers,
            data=data,
        )

        data = {
            "header:estabSelectorFrm": "header:estabSelectorFrm",
            "header:estabSelectorFrm:estab-dropdown-menu-select2:sel2": self.current_account_id,
            "header:estabSelectorFrm:selectedEstabHidden": self.current_account_id,
            "javax.faces.ViewState": self.jsf_state,
            "javax.faces.source": "header:estabSelectorFrm:estab-dropdown-menu-select2:sel2",
            "javax.faces.partial.event": "change",
            "javax.faces.partial.execute": "header:estabSelectorFrm:estab-dropdown-menu-select2:sel2 header:estabSelectorFrm:estab-dropdown-menu-select2:sel2",
            "javax.faces.partial.render": "header:estabSelectorFrm:userInfo menu:menuFrm:menu",
            "javax.faces.behavior.event": "change",
            "javax.faces.partial.ajax": "true",
        }

        self.session.post(
            "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/resumenDiario",
            headers=headers,
            data=data,
        )

    def extract_rows_and_pages(
        self, soup: BeautifulSoup
    ) -> Union[tuple[None, None], tuple[ResultSet, str]]:
        try:
            table = soup.findAll("tbody")
            if not table:
                return None, None
            pages = soup.select_one(".pager-text").text
            if not pages:
                return None, None
            rows = soup.find("table").findAll("tr")
            [_, end] = re.findall(r"\d+", pages)
            print(pages.replace("\n", ""))
            return rows, end
        except Exception as err:
            print("extract_rows:", err)
            raise LoginException()

    def next_page(self) -> BeautifulSoup:
        data = {
            "mainContent:form": "mainContent:form",
            "javax.faces.ViewState": self.jsf_state,
            "javax.faces.source": "mainContent:form:inner:resumenDiarioContent:pagerIDx:j_idt196",
            "javax.faces.partial.event": "click",
            "javax.faces.partial.execute": "mainContent:form:inner:resumenDiarioContent:pagerIDx:j_idt196 mainContent:form:inner:resumenDiarioContent:pagerIDx:j_idt196",
            "javax.faces.partial.render": "mainContent:form",
            "javax.faces.behavior.event": "action",
            "javax.faces.partial.ajax": "true",
        }

        response = self.session.post(
            "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/resumenDiario",
            headers=headers,
            data=data,
        )

        return BeautifulSoup(response.text, "lxml")

    def is_date_in_range(self, date):
        return self.start_date < date < self.end_date

    def is_payment_to_old_for_download(self, date: datetime) -> bool:
        payment_age = datetime.today() - date
        return payment_age.days > self.__PRISMA_PAYMENTS_XLS_MAX_DAYS_OLD

    def extract_payments_from_rows(self, rows):
        parser_info = parserinfo(dayfirst=True)
        payments = []
        for index, row in enumerate(rows):
            cols = row.findAll("td")
            payment_date = parse(cols[0].text, parser_info).strftime("%Y-%m-%d")
            if self.is_date_in_range(parse(payment_date)):
                img = cols[1].find("img")["src"]
                description = (
                    "VISA"
                    if "logo-900" in img
                    else "MASTERCARD"
                    if "logo-100" in img
                    else "CABAL"
                )
                payments.append(
                    {
                        "paymentId": f"cust-{self.current_account_id}-{payment_date}",
                        "accountId": self.current_account_id,
                        "branchId": self.current_account_id,
                        "description": description,
                        "salesPeriod": payment_date,
                        "paymentDate": payment_date,
                        "amount": float(cols[5].text.strip().replace(",", "")),
                        "currencyCode": "ARS",
                        "paymentDetails": {
                            "gross": float(cols[2].text.strip().replace(",", "")),
                            "fees": float(cols[3].text.strip().replace(",", "")),
                            "taxesItems": [],  # items are retrieved afterwards, from XLS file
                            "taxes": float(cols[4].text.strip().replace(",", "")),
                            "feesItems": [],  # items are retrieved afterwards, from XLS file
                        },
                    }
                )
                if not self.is_payment_to_old_for_download(parse(payment_date)):
                    download_payment_xls(self.session, self.jsf_state, index)
        return payments
