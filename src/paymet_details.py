import re

import requests


def download_payment_xls(session: requests.Session, jsf_sate: str, row: int):
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:86.0) Gecko/20100101 Firefox/86.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.8,en-US;q=0.5,en;q=0.3",
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://establecimientos.prismamediosdepago.com",
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

    data = {
        "mainContent:form": "mainContent:form",
        "javax.faces.ViewState": jsf_sate,
        "javax.faces.source": f"mainContent:form:inner:resumenDiarioContent:hideShowResumen:resumenDiarioHideShowPanel:dataTableOuter:dataTable:{row}:printExcelBtn:button",
        "javax.faces.partial.event": "click",
        "javax.faces.partial.execute": f"mainContent:form:inner:resumenDiarioContent:hideShowResumen:resumenDiarioHideShowPanel:dataTableOuter:dataTable:{row}:printExcelBtn:button mainContent:form",
        "javax.faces.partial.render": "notFindPopup scriptPrint:componentDiv",
        "javax.faces.behavior.event": "action",
        "javax.faces.partial.ajax": "true",
    }

    session.post(
        "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/resumenDiario",
        headers=headers,
        data=data,
    )

    data = {
        "mainContent:form": "mainContent:form",
        f"mainContent:form:inner:resumenDiarioContent:hideShowResumen:resumenDiarioHideShowPanel:dataTableOuter:dataTable:{row}:doPrintExcelBtn--1": "",
        "javax.faces.ViewState": jsf_sate,
    }

    response = session.post(
        "https://establecimientos.prismamediosdepago.com/establecimientos/app/services/resumenDiario",
        headers=headers,
        data=data,
    )

    output = open("test.xlsx", "wb")
    output.write(response.content)
    output.close()
    parse()


def parse():
    import openpyxl

    wb = openpyxl.load_workbook(filename="test.xlsx", data_only=True)
    a_sheet_names = wb.get_sheet_names()
    o_sheet = wb.get_sheet_by_name(a_sheet_names[0])
    deduction_and_taxes = []
    for index, cell in enumerate(o_sheet["c"]):
        value: str = cell.value
        if not value:
            continue
        is_incomplete = (
            "bito" in value
            or "1 pago" in value
            or "Ganancias" in value
            or "Bonif" in value
            or "dito en Cuotas" in value
            or "-Serv" in value
            or (
                (value.startswith("IB") or value.startswith("IVA")) and "$" not in value
            )
        )
        if is_incomplete:
            deduction_and_taxes.append(f"{value}{o_sheet['C'][index + 1].value}")
    for deduction_tax in deduction_and_taxes:
        if (
            deduction_tax.startswith("-Arancel")
            or deduction_tax.startswith("-Bonif")
            or deduction_tax.startswith("-Cargo")
            or deduction_tax.startswith("Ventas en")
            or deduction_tax.startswith("-Ventas")
            or deduction_tax.startswith("-Serv")
        ):
            desc, amount = extract_description_and_amount(deduction_tax)
            print(desc, amount)
            # print(deduction_tax)


def extract_description_and_amount(value: str):
    [description, amount] = value.replace("-", "").strip().split("$")
    return description.strip(), float(amount.strip().replace(",", ""))
