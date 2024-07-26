import json
import os
from itertools import zip_longest
from fuzzywuzzy import fuzz

class JsonComparator:
    def __init__(self, threshold, json_file_1, json_file_2) -> None:
        """
        Initializes the object with the specified threshold and JSON files.

        :param threshold: The threshold for similarity percentage.
        :param json_file_1: The path of the first JSON file.
        :param json_file_2: The path of the second JSON file.
        :return: None.
        :raises Exception: If there is an issue with loading the JSON files.
        """
    
        self.threshold = threshold
        self.json_file_1 = self.load_json(json_file_1)
        self.json_file_2 = self.load_json(json_file_2)
    
    def load_json(self, file_path):
        """
        Loads a JSON file.

        :param file_path: The file path of the JSON file.
        :return: The loaded JSON data as a Python object.
        :raises FileNotFoundError: If the JSON file does not exist.
        :raises json.JSONDecodeError: If there is an issue decoding the JSON data.
        """
        try:
            with open(file_path, 'r') as file:
                return json.load(file)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"Error: The file {file_path} does not exist.") from e
        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Error decoding JSON from file {file_path}.", e.doc, e.pos)
    
    def fuzzy_match(self, value_1, value_2):
        """
        Performs a fuzzy match between two values using the Levenshtein distance.

        This method compares two values by converting them to lowercase strings
        and calculating their similarity ratio. The ratio ranges from 0 to 100,
        where 0 indicates no similarity and 100 indicates an exact match.

        :param value_1: First string to be compared.
        :param value_2: Second string to be compared.
        :return: Ratio between 0 and 100
        :raises Exception: If ratio cannot be calculated.
        """
        try:
            value_1_string = str(value_1)
            value_2_string = str(value_2)
            lowered_value_1 = value_1_string.lower()
            lowered_value_2 = value_2_string.lower()
            return fuzz.ratio(lowered_value_1, lowered_value_2)
        except Exception as e:
            return str(e)
        
    def count_values(self, json_data):
        """
        Recursively count values in a JSON object based on their type.

        :param json_data: The JSON object to analyze (usually a dict or list)
        :return: Total number of values in JSON object.
        """
        counts = {'strings': 0, 'numbers': 0, 'booleans': 0, 'array_members': 0, 'nulls': 0}

        def recurse(data):
            """
            Recursively count values in a JSON object based on their type.

            :param json_data: The JSON object to analyze (usually a dict or list).
            :return: A dictionary with counts of strings, numbers, booleans, and array members.
            :raises None: The function does not raise any exceptions.
            """
            if isinstance(data, dict):
                for value in data.values():
                    recurse(value)
            elif isinstance(data, list):
                counts['array_members'] += len(data)
                for item in data:
                    recurse(item)
            elif isinstance(data, str):
                counts['strings'] += 1
            elif isinstance(data, bool):
                counts['booleans'] += 1
            elif isinstance(data, (int, float)):
                counts['numbers'] += 1
            elif data is None:
                counts['nulls']+=1
            
        recurse(json_data)

        total = counts['strings'] + counts['numbers'] + counts['booleans'] + counts['nulls']
        return total

    
    def compare_json(self, json_data_1, json_data_2, key_path=''):
        """
        Compares two JSON objects and returns the count of their differences and a list of differences.

        :param json_data_1: The first JSON object to compare.
        :param json_data_2: The second JSON object to compare.
        :param key_path: The key path used for tracking nested keys (default is empty string).
        :return: A tuple containing the count of differences and a list of differences.
        :raises: None.
        """
        
        # Variable holding the number of differences.
        difference_count = 0

        # List containing the differing values at the specified key.
        differences = []

        # isinstance checks to see if it is a dictionary we are searching through.
        if isinstance(json_data_1, dict):
            # Obtaining all keys in current dict.
            all_keys = set(json_data_1.keys())

            for key in all_keys:
                # Recursively iterate through the keys in the dict. 
                new_count, new_differences = self.compare_json(json_data_1[key], json_data_2[key], f"{key_path}.{key}" if key_path else key)
                difference_count += new_count
                differences.extend(new_differences)

        # isinstance to check to see if it is a list we are searching through.
        elif isinstance(json_data_1, list):
            # Recursively iterate through the list. zip_longest handles the situtation where the two lists are unequal in size. 
            # fillvalue = object() inserts placeholders in the shorter list.
            for index, items in enumerate(zip_longest(json_data_1, json_data_2, fillvalue=object())):
                item1, item2 = items
                new_count, new_differences = self.compare_json(item1, item2, f"{key_path}[{index}]")
                difference_count += new_count
                differences.extend(new_differences)

        else:
            ratio = self.fuzzy_match(json_data_1, json_data_2)
            if ratio < self.threshold:
                differences.append(f"Value difference at {key_path}: '{json_data_1}' vs '{json_data_2}'")
                return 1, differences

        return difference_count, differences

    def get_comparison(self):
        """
        Calculates the similarity percentage between two JSON files.

        :return: A string representing the similarity percentage between the two JSON files.
        :return: A list containing the keys that contain differing values.
        :raises Exception: For any other issues encountered during the comparison process.
        """
        try: 
            total_values = self.count_values(json_data=self.json_file_1)
            difference_count, differences = self.compare_json(json_data_1=self.json_file_1,json_data_2=self.json_file_2)
            
            matching_values_count = total_values - difference_count

            if total_values > 0:
                similarity_ratio = matching_values_count / total_values
                return f"{similarity_ratio * 100:.2f}% similar", differences
            else:
                return "The files do not contain keys to compare."
            
        except Exception as e:
            return str(e)