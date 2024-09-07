import calendar
import json
import os
from typing import List
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.support import expected_conditions as EC

output_final = {}
MONTH = "10"
DAY_START = 30
DAYS_TO_SELECT = 60

month_mapping = {
    "January": "01",
    "February": "02",
    "March": "03",
    "April": "04",
    "May": "05",
    "June": "06",
    "July": "07",
    "August": "08",
    "September": "09",
    "October": "10",
    "November": "11",
    "December": "12",
}


def get_days_in_month(year: int, month: int) -> int:
    """Retorna o número de dias em um mês específico do ano."""
    return calendar.monthrange(year, month)[1]


def find_month(driver: WebDriver, month: str):
    try:
        month_text = (
            WebDriverWait(driver, 10)
            .until(
                EC.presence_of_element_located(
                    (By.XPATH, "//div[@class='DayPicker-Month']")
                )
            )
            .text.split(" ")[0]
        )

        month_number = month_mapping.get(month_text, "Unknown")

        if month_number == month:
            return True
        else:
            driver.find_element(By.XPATH, "//span[@aria-label='Next Month']").click()
            return find_month(driver, month)
    except Exception as e:
        print(f"Month {month} not found after navigating: {e}")
        return False


def select_date(driver: WebDriver, day: int):
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                (By.XPATH, f"//span[@class='calender_date flex-2' and text()='{day}']")
            )
        ).click()
        print(f"Clicked on day {day}")
    except Exception as e:
        print(f"Date {day} not found: {e}")


def page_to_search(driver: WebDriver):
    try:
        WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable(
                (By.XPATH, "//a[@class='wscrOk2' and text()='Allow All']")
            )
        ).click()
    except:
        pass

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[text()='RESERVE']"))
    ).click()

    WebDriverWait(driver, 10).until(
        EC.visibility_of_element_located(
            (By.XPATH, "//div[@class='hotels-name' and text()='Jumeirah Al Naseem']")
        )
    ).click()

    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located(
            (By.XPATH, "//*[@id='room-1']/div[2]/div[1]/div/div[3]/span/img")
        )
    ).click()

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//button[text()='APPLY']"))
    ).click()

    try:
        WebDriverWait(driver, 5).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//span[@class='calender-price']")
            )
        ).text.strip() != ""
    except:
        pass


def update_output(
    output: dict, names_rooms: List[str], prices_rooms: List[str], room_size: List[str]
) -> dict:
    for i in range(len(names_rooms)):
        output[names_rooms[i]] = {"price": prices_rooms[i], "room_size": room_size[i]}
    return output


def scrape_data(driver: WebDriver, start_day, next_day, current_month):
    output = {}
    unavailable_description = None

    # Tenta fazer o scrape dos dados
    try:
        names_rooms_elements = WebDriverWait(driver, 45).until(
            EC.presence_of_all_elements_located(
                (By.XPATH, "//span[@class='content-heading-text ']")
            )
        )
        names_room = [elem.text for elem in names_rooms_elements]

        prices_rooms_elements = driver.find_elements(By.XPATH, "//div[@class='rate-price']")
        prices_rooms = [elem.text for elem in prices_rooms_elements]

        room_size_elements = driver.find_elements(
            By.XPATH, "//span[@class='hotel-size-text']"
        )
        room_size = [elem.text for elem in room_size_elements]

        output = update_output(output, names_room, prices_rooms, room_size)

    except Exception as e:
        print(f"Error scraping data: {e}")

        # Tenta encontrar a mensagem de indisponibilidade e lidar com ela
        try:
            WebDriverWait(driver, 2).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[@class='unavailable-title']")
                )
            )
            description_element = driver.find_element(By.XPATH, "//div[@class='description']")
            unavailable_description = description_element.text
            close_button = driver.find_element(By.XPATH, "//div[@class='alternate-btn']")
            close_button.click()
            print(f"Date {start_day}-{next_day}-{current_month} is unavailable: {unavailable_description}")

            # Selecionar a próxima data
            next_day_element = driver.find_element(By.XPATH, f"//span[@class='calender_date flex-2' and text()='{next_day}']")
            next_day_element.click()

        except Exception as e:
            print(f"Date {start_day}-{next_day}-{current_month} is available or issue with description: {e}")

    if unavailable_description:
        # Adicione a descrição ao JSON
        key = f"{start_day:02d}-{next_day:02d}-{current_month}"
        return {key: {"unavailable": unavailable_description}}

    return output



def save_to_json(data):
    with open('output.json', 'w') as f:
        json.dump(data, f, indent=4)



def main():
    chrome_options = Options()
    chrome_options.add_argument("--disable-search-engine-choice-screen")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-features=Cookie")
    chrome_options.add_argument("--disable-popup-blocking")

    start_day = DAY_START
    days_to_select = DAYS_TO_SELECT
    current_month = MONTH

    while days_to_select > 0:
        driver = webdriver.Chrome(options=chrome_options)
        driver.get("https://www.jumeirah.com/en")

        page_to_search_success = False
        max_retries = 5
        retries = 0

        while not page_to_search_success and retries < max_retries:
            try:
                page_to_search(driver)
                page_to_search_success = True
            except Exception as e:
                print(f"Error in page_to_search: {e}")
                retries += 1
                if retries >= max_retries:
                    print("Maximum retries reached. Exiting.")
                    return
                print(f"Retrying page_to_search ({retries}/{max_retries})...")
                driver.refresh()  # Recarrega a página em vez de criar uma nova instância

        if not find_month(driver, current_month):
            print("Failed to find the desired month.")
            driver.quit()
            return

        # Clique na data de início
        select_date(driver, start_day)

        # Clique no próximo dia
        next_day = start_day + 1
        if next_day > get_days_in_month(2024, int(current_month)):
            next_day = 1

        select_date(driver, next_day)

        # Tentar encontrar a mensagem de indisponibilidade e lidar com ela
        unavailable_description = None
        try:
            WebDriverWait(driver, 2).until(
                EC.visibility_of_element_located(
                    (By.XPATH, "//div[@class='unavailable-title']")
                )
            )
            description_element = driver.find_element(By.XPATH, "//div[@class='description']")
            unavailable_description = description_element.text
            close_button = driver.find_element(By.XPATH, "//img[@class='close-icon']")
            close_button.click()
            print(f"Date {start_day}-{next_day}-{current_month} is unavailable: {unavailable_description}")
        except Exception as e:
            print(f"Date {start_day}-{next_day}-{current_month} is available or issue with description: {e}")

        if unavailable_description:
            # Adicione a descrição ao JSON
            key = f"{start_day:02d}-{next_day:02d}-{current_month}"
            output_final[key] = {"unavailable": unavailable_description}
        else:
            try:
                discover_stays_button = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[text()='DISCOVER STAYS']")
                    )
                )
                discover_stays_button.click()
                print("Clicked on 'DISCOVER STAYS'")
            except:
                print("'DISCOVER STAYS' button not found or not clickable")
                try:
                    apply_button = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                "//div[text()='Apply' and contains(@class, 'confirm-date-cta') and contains(@class, 'date-apply-active')]",
                            )
                        )
                    )
                    apply_button.click()
                    print("Clicked on 'Apply'")
                except:
                    print("'Apply' button not found or not clickable")

            output = scrape_data(driver, start_day, next_day, current_month)

            # Criar uma chave única para o JSON como uma string
            key = f"{start_day:02d}-{next_day:02d}-{current_month}"
            output_final[key] = output

        # Fechar o navegador
        driver.quit()

        # Ajuste a data e o número de dias restantes
        start_day += 1
        days_to_select -= 1

        # Verificar a transição de mês se necessário
        if start_day > get_days_in_month(2024, int(current_month)):
            start_day = 1
            current_month = str(int(current_month) + 1).zfill(2)
            if current_month == "13":
                current_month = "01"  # Reset to January if month exceeds 12

        # Salvar os dados após cada iteração
        save_to_json(output_final)

    print("Data scraping complete.")


if __name__ == "__main__":
    main()
