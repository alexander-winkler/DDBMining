from urllib.parse import urlparse, parse_qs, quote_plus
import requests
import os
from lxml import etree

def search2API(queryurl:str, api_key:str) -> str:
    '''
    converts the url generated via the search interface of DDB
    into an API call for the DDB API
    '''
    
    if "search/organization?" in queryurl:
        endpoint = "https://api.deutsche-digitale-bibliothek.de/search/organization?"
    elif "search/person?" in queryurl:
        endpoint = "https://api.deutsche-digitale-bibliothek.de/search/person?"
    else:
        endpoint = "https://api.deutsche-digitale-bibliothek.de/search?"
    parsed_url = urlparse(queryurl)
    queries = parse_qs(parsed_url.query)
    query = " ".join(queries.get('query'))
    default_values = [f"query={quote_plus(query)}", f"oauth_consumer_key={api_key}"]
    if queries.get('facetValues[]'):
        print("facets:")
        print(queries.get('facetValues[]'))
        for facet in queries.get('facetValues[]'):
                fac, val = facet.split("=")
                default_values.append(f"facet={fac}&{fac}={quote_plus(val)}")

    return endpoint + "&".join(default_values)

def hitsAPICall(apiurl:str) -> int:
    '''
    Gibt Trefferzahl für API-Aufruf zurück.
    '''
    
    res = requests.get(apiurl + "&rows=1&offset=0")
    n = res.json().get('numberOfResults')
    print(f"Treffer für Query:\t{n}")
    return n

def infoID(ID, api_key):
    '''
    requests object info by object ID
    '''
    endpoint = f"https://api.deutsche-digitale-bibliothek.de/items/{ID}"
    par = {
        'oauth_consumer_key' : api_key
    }
    res = requests.get(endpoint, params = par)
    return res


def iterateAPICall(apiurl:str, api_key, download = False, sourcexml = True, targetdir = None) -> list:
    '''
    iterativer API-Call in 100er-Schritten. Möglichkeit des Download (bei download == True)
    Wenn sourcexml == True wird aus der Antwort die Quell-XML extrahiert und heruntergeladen,
    sonst die gesamte JSON-Antwort.
    Es ist möglich, mit targetdir einen Pfad zu definieren, in dem die Dateien gespeichert werden.
    Gibt eine Liste mit den Objekt-JSON-Dateien zurück.
    '''
    
    print("API-Call\t" + apiurl)
    
    if download and targetdir:
        if not os.path.exists(targetdir):
            os.makedirs(targetdir)
        targetdir = targetdir + "/"
    
    hits = hitsAPICall(apiurl)
    output = []
    for i in range(0,hits , 100):
        print(f"{i} bis {i+100} (von {hits})")
        res = requests.get(apiurl + f"&rows=100&offset={i}").json().get('results')[0].get('docs')
        output.extend(res)
        if download == True:
            for i in res:
                content = infoID(i.get('id'), api_key).json()
                try:
                    if sourcexml == True:
                        with open(targetdir + i.get('id') + ".xml", 'w') as OUT:
                            print(content.get('source').get('record').get('$'), file = OUT)
                            print(f"{i.get('id')}.xml written.")
                    else:
                        with open(targetdir + i.get('id') + ".json", 'w') as OUT:
                            print(content, file = OUT)
                            print(f"{i.get('id')}.json written.")
                except Exception as e:
                    print(e)
                    print(infoID(i.get('id'), api_key).url)
    return output
    
def datasetFromObject(object_ID:str, api_key) -> str:
    '''
    Funktion nimmt Objekt-Id und veranlasst den Download des dazugehörigen gesamten Datensatzes.
    '''
    res = requests.get(f"https://www.deutsche-digitale-bibliothek.de/item/xml/{object_ID}")
    dataset_ID = etree.fromstring(res.content).find(".//{http://www.deutsche-digitale-bibliothek.de/cortex}dataset-id").text
    print(f"Dataset-ID zu Objekt {object_ID} lautet: {dataset_ID}")
    apiurl = f"https://api.deutsche-digitale-bibliothek.de/search?query=dataset_id%3A%28{dataset_ID}%29&oauth_consumer_key={api_key}"
    return apiurl

def thumbFlipbook(objectlist: list, filename = "ddb_art.gif",  img_number = 10, duration = 100):
    '''
    Macht aus dem Output von iterateAPICall eine Gif-Datei.
    Beschränkung der Bilderzahl auf img_number.
    Wenn img_number = None, dann werden alle Bilder in eine Gif konvertiert.
    Dateiname der Gif kann mit "filename" verändert werden.
    Funktioniert aktuell nur bei gleichgroßen Bildern.
    '''
    from PIL import Image
    from io import BytesIO
    from time import sleep

    if img_number <= len(objectlist):
        n = img_number
    else:
        n = len(objectlist)
    
    thumbnails = []

    for x in objectlist[:n]:
        try:
            thumbnail_uuid = x.get('thumbnail')
            res = requests.get(f"https://iiif.deutsche-digitale-bibliothek.de/image/2/{thumbnail_uuid}/full/!116,87/0/default.jpg")
            img = Image.open(BytesIO(res.content))
            thumbnails.append(img)
            sleep(1)
        except Exception as e:
            print(e)
    
    if len(thumbnails) > 0:
        frame_one = thumbnails[0]
        frame_one.save(
            filename,
            format="GIF",
            append_images=thumbnails,
            save_all=True,
            duration=duration,
            loop=0
            )
    else:
        print("Keine Thumbnails vorhanden.")
        
