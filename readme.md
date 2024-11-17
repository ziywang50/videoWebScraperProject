# Youtube Video Product Scraper

Video WebScraper scrapes product-related information given a youtube video. It clicks on each link in
the youtube description and is able to search the product-related information and store in a json file.
In this project, I assume that all product-related links are already opened in a product page with one 
product, with an image, a product title and a product price. If a video is missing some information (e.g. missing product price and img),
then it will not be stored in the json file. 

For all websites except for amazon, I made a simple searcher by searching through selenium on different html tags.
The generic scraper is slower and for more generic pages.

### Methods:
For now, this method assumes that the product buying page is already opened, meaning that no extra clcking is done.
For amazon, I created it by searching up not only the main product, but also the related products of the main product. 
Sometimes amazon uses reCaptcha to block, so I used a library called AmazonCaptcha to fix it.

For other websites, I am assuming the product page is already opened, and with one 
product, with an image, a product title and a product price. If there are multiple products, then it will probably pick the 
first one. The method is to search across multiple tags, like <img> for images, <span>, <strong> .... for prices, etc.
After searching on all possible tags, I will use some methods, like regex for a valid price, text model for a valid product,
and clip model for the similarity of image and product. If some error occurs during the searching progress, it will skip the current
and move onto the next.


### Disclaimer:
This project is used for and personal research and educational use.

### Use Guide
```
Clone the project 
conda create -n webc python=3.11.0
conda activate webc
pip install -r requirements.txt
```
To run the script
```
python extract_product_details.py
```
Link for demo video
https://drive.google.com/file/d/18BKEwXRUjLv5VuqUmgYAG6bbZCru5z9M/view?usp=sharing

