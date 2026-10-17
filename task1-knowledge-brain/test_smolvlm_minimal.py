
from parsing.image_processor import process_article_images

url = (
    "https://www.brilliantdirectories.com/wp-content/uploads/2016/11/marketplacebannertest6.jpg"
)

results = process_article_images([url])

for result in results:
    print("\nImage URL:", result["url"])
    print("Description:", result.get("description"))
    print("Error:", result.get("error", "None"))
