from typing import Union

import requests

from src.login import do_login
from dateutil.parser import parse, parserinfo
from datetime import datetime, timedelta
from src.login_exception import LoginException
from bs4 import BeautifulSoup, ResultSet
import re

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
    "Referer": "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/transaccionesPresentadas",
}


def get_orders(
    session: requests.Session,
    accounts: list[dict[str, str]],
    start_date=None,
    end_date=None,
):
    orders = []
    failed_accounts = []
    retry = 2  # TODO: should be an env var
    for _, account in enumerate(accounts):
        for index in range(retry):
            try:
                fetched_orders = fetch_orders(
                    session, account["id"], start_date, end_date
                )
                orders.extend(fetched_orders)
                break
            except LoginException:
                print("\n >>> RE LOGIN <<< \n")
                session = do_login()
                if index == 2:
                    failed_accounts.append(account["id"])
    orders_without_dups = remove_duplicated_orders(orders)
    return orders_without_dups


def remove_duplicated_orders(orders: list[dict[str, str]]) -> list[dict[str, str]]:
    result = []
    seen = set()
    for order in orders:
        key = order["orderId"]
        if key in seen:
            continue
        result.append(order)
        seen.add(key)
    return result


def fetch_orders(
    session, account_id, start_date: str, end_date: str
) -> list[dict[str, str]]:
    print("~ account %s ~" % account_id)
    jsf_view_state = change_account(session, account_id)

    print("~ get orders ~")
    orders = []
    date_chunks = split_dates_in_chunks(start_date, end_date)

    for (start_date, end_date) in date_chunks:
        print("Fetch range %s - %s" % (start_date, end_date))
        response = filter_presented_orders(
            session, jsf_view_state, start_date, end_date
        )
        rows, pages = extract_rows(response)
        if rows is not None:
            extracted_orders = extract_orders(rows, account_id)
            orders.extend(extracted_orders)
            if pages is not None:
                [_, end] = re.findall(r"\d+", pages)
                for _ in range(1, int(end)):
                    response = next_page(session, jsf_view_state, start_date, end_date)
                    rows, _ = extract_rows(response)
                    extracted_orders = extract_orders(rows, account_id)
                    orders.extend(extracted_orders)
    print("~ fetched %s orders for account %s ~\n" % (len(orders), account_id))
    return orders


def filter_presented_orders(
    session: requests.Session, jsf_view_state: str, start_date: str, end_date: str
) -> requests.Response:
    data = {
        "mainContent:form": "mainContent:form",
        "mainContent:form:inner:searchTrans:dFrom:input": start_date,
        "mainContent:form:inner:searchTrans:dTo:input": end_date,
        "mainContent:form:inner:searchTrans:j_idt146:input": "",
        "mainContent:form:inner:searchTrans:j_idt155:input": "",
        "mainContent:form:inner:searchTrans:j_idt159:input": "",
        "javax.faces.ViewState": jsf_view_state,
        "javax.faces.source": "mainContent:form:inner:searchTrans:j_idt161",
        "javax.faces.partial.event": "click",
        "javax.faces.partial.execute": "mainContent:form:inner:searchTrans:j_idt161 "
        "mainContent:form:inner:searchTrans:contentBody",
        "javax.faces.partial.render": "mainContent:form:inner:transaccionesContent:outer export-form "
        "mainContent:form:inner:transaccionesContent:liqTotals:totalBarSubTotals "
        "mainContent:form:inner:transaccionesContent:liqTotals:totalBarTotals "
        "mainContent:form:inner:searchTrans:outer",
        "javax.faces.behavior.event": "action",
        "javax.faces.partial.ajax": "true",
    }
    response = session.post(
        "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/transaccionesPresentadas",
        headers=headers,
        data=data,
    )
    return response


def goto_presented_orders(session: requests.Session) -> str:
    print("~ go to presented orders ~")
    response = session.get(
        "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/transaccionesPresentadas",
        headers=headers,
    )
    soup = BeautifulSoup(response.text, "html.parser")
    jsf_view_state = soup.find("input", {"id": "javax.faces.ViewState"}).get("value")
    return jsf_view_state


def extract_rows(
    response: requests.Response,
) -> Union[tuple[None, None], tuple[ResultSet, str]]:
    soup = BeautifulSoup(response.text, "lxml")
    try:
        table = soup.findAll("tbody")
        if not table:
            return None, None
        rows = soup.find("table").findAll("tr")
        pages = soup.select_one(".pager-text").text
        print(pages.replace("\n", ""), end="\r")
        return rows, pages
    except Exception as err:
        print("extract_rows:", err)
        raise LoginException()


def next_page(
    session: requests.Session, jsf_state: str, start_date: str, end_date: str
) -> requests.Response:
    data = {
        "mainContent:form": "mainContent:form",
        "mainContent:form:inner:searchTrans:dFrom:input": start_date,
        "mainContent:form:inner:searchTrans:dTo:input": end_date,
        "mainContent:form:inner:searchTrans:j_idt146:input": "",
        "mainContent:form:inner:searchTrans:j_idt155:input": "",
        "mainContent:form:inner:searchTrans:j_idt159:input": "",
        "javax.faces.ViewState": jsf_state,
        "javax.faces.source": "mainContent:form:inner:transaccionesContent:pagerIDx:j_idt240",
        "javax.faces.partial.event": "click",
        "javax.faces.partial.execute": "mainContent:form:inner:transaccionesContent:pagerIDx:j_idt240 "
        "mainContent:form:inner:transaccionesContent:pagerIDx:j_idt240",
        "javax.faces.partial.render": "mainContent:form",
        "javax.faces.behavior.event": "action",
        "javax.faces.partial.ajax": "true",
    }

    return session.post(
        "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/transaccionesPresentadas",
        headers=headers,
        data=data,
    )


def extract_orders(rows: ResultSet, account_id: str) -> list[dict[str, str]]:
    try:
        order_rows = []
        for row in rows:
            cols = row.findAll("td")
            order_row = extract_order_row(cols)
            order_rows.append(order_row)
        parsed_orders = []
        for row in order_rows:
            parsed_orders.append(parse_order(account_id, row))
        return parsed_orders
    except Exception as err:
        print("extract_orders:", err)
        raise LoginException()


def extract_order_row(cols: list[ResultSet]) -> dict[str, str]:
    order = {
        "presentedDate": cols[0].text.strip(),
        "batch": cols[1].text.strip(),
        "paymentDate": cols[2].text.strip(),
        # "cardBrand": (cardBrandImgUrl === undefined
        #               ? undefined: cardBrandImgUrl.includes('logo-900')
        #               ? 'VISA': cardBrandImgUrl.includes('logo-100')
        #               ? 'MASTERCARD': 'CABAL') as CardBrand,
        "description": cols[4].text.strip(),
        "originalDate": cols[5].text.strip(),
        "voucherNumber": cols[6].text.strip(),
        "cardNumber": cols[7].text.strip(),
        "installmentsPlan": cols[8].text.strip(),
        "amount": cols[9].text.strip(),
    }
    return order


def parse_order(account_id: str, row: dict[str, str]) -> dict[str, str]:
    payment_date = parse(row["paymentDate"]).strftime("%Y-%m-%d")
    return {
        "presentedDate": payment_date,
        "batch": row["batch"],
        "paymentDate": payment_date,
        # TODO
        # "cardDate": row["cardBrand"],
        "description": row["description"],
        "branchId": account_id,
        "date": parse(row["originalDate"]).strftime("%Y-%m-%d"),
        "orderId": build_order_id(account_id, payment_date, row["voucherNumber"]),
        "paymentId": payment_date,
        "voucherName": row["voucherNumber"],
        "cardNumber": row["cardNumber"],
        "amount": float(row["amount"].replace(",", "")),
        "currencyCode": "ARS",
        "accountId": account_id,
    }


def build_order_id(account_id: str, payment_id: str, voucher_number: str) -> str:
    return "cust-order-acc_%s-p_%s-v_%s" % (account_id, payment_id, voucher_number)


def change_account(session: requests.Session, next_account_id: str) -> str:
    jsfState = goto_presented_orders(session)

    data = {
        "header:estabSelectorFrm": "header:estabSelectorFrm",
        "header:estabSelectorFrm:estab-dropdown-menu-select2:sel2": next_account_id,
        "header:estabSelectorFrm:selectedEstabHidden": next_account_id,
        "javax.faces.ViewState": jsfState,
        "javax.faces.source": "header:estabSelectorFrm:estabSelected",
        "javax.faces.partial.event": "click",
        "javax.faces.partial.execute": "header:estabSelectorFrm:estabSelected header:estabSelectorFrm:userInfo",
        "javax.faces.partial.render": "@all",
        "javax.faces.behavior.event": "action",
        "javax.faces.partial.ajax": "true",
    }

    session.post(
        "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/transaccionesPresentadas",
        headers=headers,
        data=data,
    )

    data = {
        "header:estabSelectorFrm": "header:estabSelectorFrm",
        "header:estabSelectorFrm:estab-dropdown-menu-select2:sel2": next_account_id,
        "header:estabSelectorFrm:selectedEstabHidden": next_account_id,
        "javax.faces.ViewState": jsfState,
        "javax.faces.source": "header:estabSelectorFrm:estab-dropdown-menu-select2:sel2",
        "javax.faces.partial.event": "change",
        "javax.faces.partial.execute": "header:estabSelectorFrm:estab-dropdown-menu-select2:sel2 header:estabSelectorFrm:estab-dropdown-menu-select2:sel2",
        "javax.faces.partial.render": "header:estabSelectorFrm:userInfo menu:menuFrm:menu",
        "javax.faces.behavior.event": "change",
        "javax.faces.partial.ajax": "true",
    }

    session.post(
        "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/transaccionesPresentadas",
        headers=headers,
        data=data,
    )

    # soup = BeautifulSoup(x.text, "lxml")
    # print(soup.prettify())
    return jsfState


def split_dates_in_chunks(start_date: str, end_date: str) -> list[tuple[str, str]]:
    parser_info = parserinfo(dayfirst=True)
    start_date = parse(start_date, parser_info)
    end_date = parse(end_date, parser_info)

    prior_90_days = datetime.today() - timedelta(days=90)

    start_date = prior_90_days if start_date < prior_90_days else start_date
    end_date = datetime.today() if end_date <= start_date else end_date

    date_modified = start_date
    date_range = []
    while date_modified < end_date:
        tmp = date_modified
        date_modified += timedelta(days=30)
        if date_modified > end_date:
            date_modified = end_date
        date_range.append(
            (tmp.strftime("%d/%m/%Y"), date_modified.strftime("%d/%m/%Y"))
        )

    return date_range
