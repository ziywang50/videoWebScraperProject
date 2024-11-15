# Youtube Video Product Scraper

Video WebScraper scrapes product-related information given a youtube video. It clicks on each link in
the youtube description and is able to search the product-related information and store in a json file.
In this project, I assume that all product-related links are already opened in a product page with one 
product, with an image, a product title and a product price. 
For all websites except for amazon, I made a simple searcher by searching through selenium on different html tags.
The generic scraper is slower and for more generic pages. 

### Disclaimer:
This project is used for and personal research and educational use.

### Use Guide
```
Clone the project 
conda create -n webc python=3.11.0
conda activate webc
pip install -r requirements.txt
```

