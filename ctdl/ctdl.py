import sys
import argparse
import requests
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from downloader import download_series, download_parallel
from utils import FILE_EXTENSIONS, THREAT_EXTENSIONS

search_url = "https://www.google.com/search"

s = requests.Session()
# Max retries and back-off strategy so all requests to http:// sleep before retrying
retries = Retry(total=5,
                backoff_factor=0.1,
                status_forcelist=[ 500, 502, 503, 504 ])
s.mount('http://', HTTPAdapter(max_retries=retries))


def scrape(html):
	soup = BeautifulSoup(html, 'lxml')
	results = soup.findAll('h3', {'class': 'r'})
	links = []
	for result in results:
		link = result.a['href'][7:].split('&')[0]
		links.append(link)
	return links


def get_links(limit, params, headers):
    """
    every Google search result page has a start index.
    every page contains 10 search results.
    """
    links = []
    for start_index in range(0, limit, 10):
        params['start'] = start_index
        resp = s.get(search_url, params = params, headers = headers)
        page_links = scrape(resp.content)
        links.extend(page_links)
    return links[:limit]


def validate_links(links):
    valid_links = []
    for link in links:
        if link[:7] in "http://" or link[:8] in "https://":
            valid_links.append(link)
    return valid_links


def search(query, file_type = 'pdf', limit = 10):
    gquery = "filetype:{0} {1}".format(file_type, query)
    params = {
        'q': gquery,
        'start': 0,
    }
    headers = {
        'User Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:53.0) \
        Gecko/20100101 Firefox/53.0'
    }
    links = get_links(limit, params, headers)
    valid_links = validate_links(links)
    return valid_links


def check_threats(**args):
    is_high_threat = False
    for val in THREAT_EXTENSIONS.values():
        if type(val) == list:
            for el in val:
                if args['file_type'] == el:
                    is_high_threat = True
                    break
        else:
            if args['file_type'] == val:
                is_high_threat = True
                break
    return is_high_threat


def validate_args(**args):
    if not args['query']:
        print("\nMissing required query argument.")
        sys.exit()


def download_content(**args):
    if not args['directory']:
        args['directory'] = args['query'].replace(' ', '-')

    print("Downloading {0} {1} files on topic {2} and saving to directory: {3}"
        .format(args['limit'], args['file_type'], args['query'], args['directory']))

    links = search(args['query'], args['file_type'], args['limit'])

    if args['parallel']:
        download_parallel(links, args['directory'])
    else:
        download_series(links, args['directory'])


def show_filetypes(extensions):
    for item in extensions.items():
        val = item[1]
        if type(item[1]) == list:
            val = ", ".join(str(x) for x in item[1])
        print("{0:4}: {1}".format(val, item[0]))


def main():
    parser = argparse.ArgumentParser(description = "Content Downloader",
    								 epilog="Now download files on any topic in bulk!")
 
    # defining arguments for parser object
    parser.add_argument("query", type = str, default = None, nargs = '?',
    					help = "Specify the query.")

    parser.add_argument("-f", "--file_type", type = str, default = 'pdf',
                        help = "Specify the extension of files to download.")
     
    parser.add_argument("-l", "--limit", type = int, default = 10,
                        help = "Limit the number of search results (in multiples of 10).")
     
    parser.add_argument("-d", "--directory", type = str, default = None,
                        help = "Specify directory where files will be stored.")

    parser.add_argument("-p", "--parallel", action = 'store_true', default = False,
                        help = "For parallel downloading.")

    parser.add_argument("-a", "--available", action='store_true',
    					help = "Get list of all available filetypes.")

    parser.add_argument("-t", "--threats", action='store_true',
                        help = "Get list of all common virus carrier filetypes.")

    args = parser.parse_args()
    args_dict = vars(args)

    if args.available:
        show_filetypes(FILE_EXTENSIONS)
        return

    if args.threats:
        show_filetypes(THREAT_EXTENSIONS)
        return

    high_threat = check_threats(**args_dict)

    if high_threat:
        def prompt(message, errormessage, isvalid, isexit):
            res = None
            while res is None:
                res = input(str(message)+': ')
                if isexit(res):
                    sys.exit()
                if not isvalid(res):
                    print(str(errormessage))
                    res = None
            return res
        prompt(
            message = "WARNING: Downloading this file type may expose you to a heightened security risk.\nPress 'y' to proceed or 'n' to exit",
            errormessage= "Error: Invalid option provided.",
            isvalid = lambda x:True if x is 'y' else None,
            isexit = lambda x:True if x is 'n' else None
        )

    validate_args(**args_dict)
    download_content(**args_dict)


if __name__ == "__main__":
    main()
