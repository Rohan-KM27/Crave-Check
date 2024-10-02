import ast
from flask import render_template, request
import pandas as pd
import io, base64
from PIL import Image
import re
import google.generativeai as genai
from tabulate import tabulate
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

genai.configure(api_key=os.getenv('api_key'))
model = genai.GenerativeModel("gemini-1.5-flash")


def product_details(image_path,name,username):
    myfile = genai.upload_file(image_path)
    
    # Advanced prompt engineering to get a detailed product name with tagline/flavor
    prompt = f"""
    Crefully analyze the product displayed in the provided image and extract the **complete product name** along with any associated **tagline, flavor, or variation**. Ensure the output includes specific descriptors like flavor, type, or any additional product details. 
    For example, instead of simply outputting 'ARUN ICE CREAMS', the result should include the flavor as in 'ARUN ICE CREAMS PISTA FLAVORED'.
    Image File: {myfile}
    Only return the product name and details with no additional text or explanation.
    """
    
    # Generate the response using the Gemini API with the provided prompt
    product_name = model.generate_content([myfile, prompt])

    if 'not' in product_name.text:
        return render_template('scan_image.html', name=name, username=username,error_message=product_name)

    # prompt for extracting nutrition and ingredient information
    nutri_extract_prompt = f"""
    Analyze the nutrition label from the image file carefully : {myfile}. 
    I need a detailed breakdown of the nutritional content in the image, formatted in JSON. 
    Include the following details:
    
    1. List of nutrients with their corresponding values and units.
    2. The percentage of each nutrient compared to the daily recommended intake (assuming 100% as the daily requirement).
    3. A summary table showing the percentage of each nutrient in relation to 100%.
    4. Detailed ingredients list with any flagged or concerning ingredients highlighted (e.g., high sugar content, allergens, preservatives).
    """
    
    # Generate the content
    product_info = model.generate_content([myfile, "\n\n", nutri_extract_prompt])
    
    # Craft the prompt to map the information into the Product Information Data Set
    data_mapping_prompt = f"""
    The following is the product image and product information that needs to be mapped to a Product Information Data Set. Analyze the extracted details from the image carefully and map them to the respective fields in JSON format.
    product Image: {myfile}
    Extracted Information: {product_info}
    Product Information Data Set Structure:
    1. Allergy_Gluten (0 or 1)
    2. Allergy_Peanuts (0 or 1)
    3. Allergy_Tree Nuts (0 or 1)
    4. Allergy_Dairy (0 or 1)
    5. Allergy_Eggs (0 or 1)
    6. Allergy_Shellfish (0 or 1)
    7. Allergy_Fish (0 or 1)
    8. Allergy_Soy (0 or 1)
    9. Allergy_Wheat (0 or 1)
    10. Allergy_Sesame (0 or 1)
    11. Vegetarian (0 or 1)
    12. Non-Vegetarian (0 or 1)
    13. Vegan (0 or 1)
    14. Lactose Intolerance (0 or 1)
    15. Gluten Sensitivity (0 or 1)
    16. Diabetes (0 or 1)
    17. High Cholesterol (0 or 1)
    18. Heart Conditions (0 or 1)
    19. Obesity(0 or 1)
    20. Kidney Disease (0 or 1)
    21. Hypertension (0 or 1)
    22. Jain (0 or 1)
    23. Organic (0 or 1)
    Please map the ingredients or descriptions from the Product Image Extracted Information to the corresponding fields above carefully and just return a list in the format of 
    
    [[Allergy_Gluten (0 or 1), Allergy_Peanuts (0 or 1), Allergy_Tree Nuts (0 or 1), Allergy_Dairy (0 or 1), Allergy_Eggs (0 or 1), Allergy_Shellfish (0 or 1), Allergy_Fish (0 or 1), Allergy_Soy (0 or 1), Allergy_Wheat (0 or 1), Allergy_Sesame (0 or 1)], 
     [Vegetarian or Non-Vegetarian or Vegan or Lactose-Intolerance or Gluten-Sensitivity], //Don't make any unnecessary assumptions here. should be cristal clear.  
     [Diabetes (0 or 1), High-Cholesterol (0 or 1), Heart-Conditions (0 or 1), Obesity(0 or 1), Kidney-Disease (0 or 1), Hypertension (0 or 1)],
     [Jain (0 or 1)],
     [Organic (0 or 1)]]
    without any preamble response.
     (Consider dairy products like milk/curd/ghee/butter/.. as vegetarian).
    """
    
    # Generate response from the Gemini API
    product_data = model.generate_content([myfile, product_info.text, "\n\n", data_mapping_prompt])

    # Parse result if necessary and return the structured data
    return product_name.text,product_data.text

def check_product_safety(product_info, user_info=None):
    # Handle case when user_info is not provided or is empty
    if not user_info:
        user_info_str = "No specific user information provided. The product safety is evaluated based on common allergens and health conditions."
        personalization = "Since you did not provide specific information, the evaluation is based on general safety standards."
    else:
        # Convert the user_info dictionary to a readable string
        user_info_str = "\n".join([f"{key}: {value}" for key, value in user_info.items()])
        personalization = "Considering your specific allergies and health conditions."

    # Convert the product_info list to a readable string
    product_info_str = str(product_info)

    # Create the prompt string for the model
    prompt = f"""
    Based on the following information about you:
    {user_info_str}

    And the following product information: (Product details in the form of [[Allergy_Gluten (0 or 1), Allergy_Peanuts (0 or 1), Allergy_Tree Nuts (0 or 1), Allergy_Dairy (0 or 1), Allergy_Eggs (0 or 1), Allergy_Shellfish (0 or 1), Allergy_Fish (0 or 1), Allergy_Soy (0 or 1), Allergy_Wheat (0 or 1), Allergy_Sesame (0 or 1)],
    [Vegetarian/Non-Vegetarian/Vegan/Lactose-Intolerance/Gluten-Sensitivity],
    [Diabetes (0 or 1), High-Cholesterol (0 or 1), Heart-Conditions (0 or 1), Obesity (0 or 1), Kidney-Disease (0 or 1), Hypertension (0 or 1)],
    [Jain (0 or 1)],
    [Organic (0 or 1)]]):
    {product_info_str}

    Carefully determine whether it is safe for you to consume the product, considering your allergies, dietary restrictions, and health conditions (Consider Dairy products like milk, cheese, yogurt, and butter as vegetarian).
    
    {personalization}
    
    - If the product has *5 or more total matches* (from allergies, dietary preferences, or health conditions), return 'LOOK FOR ALTERNATIVES' and explain that it might not be safe for consumption.
    - If the product has *fewer than 5 matches*, return 'CAUTIOUS' and suggest it may still cause issues.
    - If there are no significant risks, return 'YES' and explain that the product is safe to consume.

    Please return CONSUME (YES/CAUTIOUS/NO) and a personalized remark on why it is safe/unsafe/cautious (strictly limited to 50 to 80 words without any preambles, using "you" and "your" language when user info is provided, or generic terms w.r.t the prodct_info otherwise) in a list with each word as an element in it (REMARK = ['str1', 'str2'..]).
    """

    # Call the model with the generated prompt
    result = model.generate_content(prompt)  

    product_report=result.text

    consume_start = product_report.index("['") + 2
    consume_end = product_report.index("']", consume_start)
    consume_result = product_report[consume_start:consume_end]

    remark_start = product_report.index("REMARK = ['") + 10
    remark_end = product_report.index("']", remark_start)
    remark_list = product_report[remark_start:remark_end].split(', ')
    remark_result = ' '.join(word.strip("'") for word in remark_list)

    print(f"the remark result:{remark_result}")
    
    return consume_result,remark_result


def analyze_product_and_environmental_impact_from_image(image_path):
    """
    Function to extract product content (ingredients, components, nutritional info) and provide additional
    information including consumption eligibility, nutrition value, health effects, and alternative products,
    returning the data as specified.
    """
    myfile = genai.upload_file(image_path)

    prompt = f"""
    You are given an image containing a product label that lists ingredients, components, or nutritional information.
    This product can be either a food item or a personal care product.

    Your task is to:

    1. Determine if the product is food.
       - Return 'YES' if the product is a consumable food, 'NO' otherwise.
    
    2. Extract the ingredients/components from the label.
       - List each ingredient or component under a list named 'ingredients_list'.
    
    3. Extract the nutrition value if present.
       - List the nutritional values (e.g., calories, fats, proteins, carbohydrates) and return them as a dictionary
         with the following format: ('Nutrient': 'Amount').
       - Example: ('Calories': '200 kcal', 'Fats': '10g', 'Proteins': '5g', 'Carbohydrates': '30g').
    
    4. For each ingredient or component, generate a detailed description of its effects on health.
       - Provide brief descriptions of how the component impacts health, with a minimum of 20 words and a maximum of 30 words.
       - List each description under a list named 'health_effects_list'.
    
    5. Suggest alternative products that can be used instead of this product, if possible.
       - List each alternative product under 'alternative_products_list'.

    Return the results in the following format:
       - A list that contains five elements: 
       [the consumption eligibility ('YES' or 'NO'),
        the ingredients list,
        the nutrition value as a dictionary,
        the health effects list,
        the alternative products list]
       - Example format: ['YES', [ingredient1, ingredient2, ...], nutrition_value_dict, [health_effects1, health_effects2, ...], [alt_product1, alt_product2, ...]].
       - Make sure to that number of opening brackets should match the closing one and there should be even numbers of quotes
    6. Ignore any irrelevant or decorative text present on the label.
    7. Ensure the components are correctly matched with both their nutrition and health-related details.
    
    Image for processing: {myfile}
    """
    response = model.generate_content([myfile, "\n\n", prompt])
    striped_response = response.text.strip()
    extracted_data = re.sub(r'```json|```', '', striped_response).strip().replace("'", '"').replace("‘", '"').replace("’", '"')
    cleaned_data = ast.literal_eval(extracted_data)
    try:
        data = clean_extracted_data(cleaned_data)
        if len(data) != 5:
            return f"Error: Expected 5 elements in the response, but got {len(data)}."

        # Assign extracted data to variables
        consumable = data[0]
        ingredients = data[1]
        nutrition_value = data[2]
        health_effects = data[3]
        alternative_products = data[4]

        # Convert the nutrition dictionary into a DataFrame
        nutrition_df = pd.DataFrame(list(nutrition_value.items()), columns=["Nutrient", "Amount"])

        return consumable, ingredients, nutrition_df, health_effects, alternative_products

    except (SyntaxError, ValueError) as e:
        return f"\nError: {str(e)}. Response: {cleaned_data}"
    except Exception as e:
        return f"Error processing response: {e}"

def clean_extracted_data(extracted_data):
    # Clean the extracted data
    cleaned_data = []
    
    # Clean the status
    cleaned_status = extracted_data[0].strip().upper()  # Normalize to uppercase
    cleaned_data.append(cleaned_status)
    
    # Clean the ingredients
    cleaned_ingredients = [ingredient.strip().title() for ingredient in extracted_data[1]]
    cleaned_data.append(cleaned_ingredients)
    
    # Clean the nutritional info, keeping it as is (if not empty)
    cleaned_nutritional_info = extracted_data[2] if isinstance(extracted_data[2], dict) else {}
    cleaned_data.append(cleaned_nutritional_info)
    
    # Clean health effects
    cleaned_health_effects = [effect.strip() for effect in extracted_data[3]]
    cleaned_data.append(cleaned_health_effects)
    
    # Clean alternative products
    cleaned_alternatives = [product.strip().title() for product in extracted_data[4]]
    cleaned_data.append(cleaned_alternatives)
    
    return cleaned_data