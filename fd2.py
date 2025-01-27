from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import pandas as pd
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from typing import Annotated
from typing_extensions import TypedDict
import re

# Set up environment variables
langsmith = "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"
os.environ["LANGCHAIN_API_KEY"] = langsmith
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_PROJECT"] = "DMCCLanggraph"

# Initialize LLM
llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0,
               groq_api_key="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")

# Load dataset
food_data = pd.read_csv("nutrients_csvfile.csv")

# Define input schema
class QueryPayload(BaseModel):
    query: str

# Define FastAPI application
app = FastAPI()

# Define a function to find foods based on nutrients
def find_foods_for_nutrient(nutrient: str, quantity: float):
    # Check if the column exists
    if nutrient not in food_data.columns:
        return None

    # Filter the food dataset based on the nutrient quantity
    matching_foods = food_data[food_data[nutrient] >= quantity]
    return matching_foods

# Endpoint for handling user queries
@app.post("/query/")
async def process_query(payload: QueryPayload):
    user_query = payload.query

    # Use regex to extract the nutrient and quantity from the query
    nutrient_query_regex = r"(\\d+\\.?\\d*)\\s*(grams?|g|calories?|kcal|fat|carbs?|protein)"
    match = re.match(nutrient_query_regex, user_query, re.IGNORECASE)

    # Default response if no nutrient query is detected
    response_content = ""
    if match:
        # Extract the quantity and nutrient from the matched regex groups
        quantity = float(match.group(1))
        nutrient = match.group(2).lower()

        # Map user-friendly input to column names (e.g., "protein" -> "Protein")
        nutrient_map = {
            "protein": "Protein",
            "calories": "Calories",
            "fat": "Fat",
            "carbs": "Carbs",
        }

        # Normalize the nutrient to match the dataset column names
        nutrient = nutrient_map.get(nutrient, nutrient)

        # Get a list of foods that match the nutrient requirement
        matching_foods = find_foods_for_nutrient(nutrient, quantity)

        if matching_foods is None:
            response_content = f"Sorry, '{nutrient}' is not a valid nutrient in the dataset."
        elif matching_foods.empty:
            response_content = f"Sorry, no foods found with at least {quantity} of {nutrient}."
        else:
            # Generate the response with the food list
            food_list_str = "\n".join([
                f"{row['Food']} - {row[nutrient]} {nutrient.lower()}"
                for _, row in matching_foods.iterrows()
            ])
            response_content = f"Here are some foods with at least {quantity} {nutrient.lower()}:\n{food_list_str}"

    # If no nutrient query, pass the query to the LLM
    state = {"messages": [{"role": "user", "content": user_query}]}
    try:
        llm_response = llm.invoke(state["messages"])
        response_content += f"\n\nLLM Response: {llm_response.content}"
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error invoking LLM: {e}")

    return {"response": response_content}
if __name__ =="__manin__":
    import uvicorn
    uvicorn.run(app,host= "0.0.0.0",port=8000)