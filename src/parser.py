from bs4 import BeautifulSoup, Tag
import dill
import pandas as pd
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class HtmlParserCustom:

    def __init__(self) -> None: pass


    @staticmethod
    def parse_contents(contents: Dict[str, dict]) -> pd.DataFrame:
        dfs = []
        for k, c in contents.items():
            logger.info(f"Custom parsing the content for url {k}")
            dfs.append(HtmlParserCustom.parse_content(c['content'], k))
        df = pd.concat(dfs)
        return df

    @staticmethod
    def parse_content(content: str, orig_url: str) -> pd.DataFrame:
        soup = BeautifulSoup(content, "html.parser")

        tables = soup.find_all("div", attrs={"class": "mb-4 shadow"})
        if tables is not None:
            parsed_content = []
            for table in tables:
                search_term_node = {"class": "col-sm-3 col-lg-2"}
                search_term_name = {"class": "col-sm-9 col-lg-2"}
                node = table.find("div", attrs=search_term_node).text.strip() if table.find("div", attrs=search_term_node) is not None else "No node found"
                name = table.find("div", attrs=search_term_name).text.strip() if table.find("div", attrs=search_term_name) is not None else "No name found"
                parsed_content.append({
                    "node": node,
                    "name": name, 
                    "type": "header",
                    "url": orig_url,
                    "search_term_node": search_term_node,
                    "search_term_name": search_term_name
                })
            

                table_rows = table.find_all("div", attrs={"class": "rowgroup"})
                if table_rows is not None:
                    for row in table_rows:
                        search_term_row_name = {"class": "col-lg-10"}
                        node =  row.find("div", attrs=search_term_node).text.strip() if  row.find("div", attrs=search_term_node) is not None else "No node found"
                        name =  row.find("div", attrs=search_term_row_name).text.strip() if  row.find("div", attrs=search_term_row_name) is not None else "No name found"
                        parsed_content.append(
                            {
                                "node": node,
                                "name": name,
                                "type": "row",
                                "url": orig_url,
                                "search_term_node": search_term_node,
                                "search_term_name": search_term_row_name
                            }
                        )
        else:
            parsed_content = []
        df = pd.DataFrame(parsed_content)
        return df



if __name__ == '__main__':
    dfs = []
    for db_year in (2025, 2024, 2023, 2022, 2021, 2020):
        with open(f"./tmp/result_crawling_6000_seconds_{db_year}.pickle", "rb") as f:
            crawl_res = dill.load(f)

        p = HtmlParserCustom()
        df = p.parse_contents(crawl_res['pages'])
        # some df processing 
        df["node_clean"] = (
            df['node']
            .str.replace("Chapter", "", regex=False)
            .str.replace("Position", "", regex=False)
            .str.replace("Subheading", "", regex=False)
            .replace(r"\s+", "", regex=True)
        )
        df["year"] = db_year
        df = df.query("node != 'No node found' and name != 'No name found'" )
        dfs.append(df)
    df_fin = pd.concat(dfs)
    df_fin = df_fin.drop_duplicates(subset=["node_clean", "year", "type"])
    print(df_fin)
    df_fin.to_csv("./tmp/hs_codes_2025_to_2021_full.csv", index=False)



    
        