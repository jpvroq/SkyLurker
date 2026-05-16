import netcreep
import json

if __name__ == "__main__":
    config = {
        "base_url": "https://adsb.lol/",
        "type": "dynamic",
            "jobs": [{
                "type": "table",
                "url_pattern": "",
                "name": "planesTable",
                "pre_actions": [
                    {
                        "action": "click_if_not_checked",
                        "value": "#allTableLines_cb",
                        "check": "settingsCheckboxChecked"
                    },
                    {
                        "action": "click",
                        "value": ".ol-zoom-out",
                        "check": 10
                    },
                    {
                        "action": "wait",
                        "value": 1000
                    }
                ]
            }]
    }
    crawler = netcreep.CreepFactory.create(config)
    crawler.connect()
    result = crawler.lurk()
    crawler.close()
    json_res = json.dump(result, indent=4, ensure_ascii=False)
    print(json_res)