#!/usr/bin/env python3
"""
Strategy manager for drone scanning patterns.
"""
import json
import os

class StrategyManager:
    """
    Manages drone scanning strategies loaded from a JSON file.
    """
    def __init__(self, strategy_file="configs/cameras.json"):
        """
        Initialize the strategy manager.
        
        Args:
            strategy_file (str): Path to the JSON file containing strategies
        """
        self.strategies = {}
        self.default_strategy = "1080p"  # Default strategy if none specified
        self._load_strategies(strategy_file)
        
    def _load_strategies(self, strategy_file):
        """
        Load strategies from JSON file.
        
        Args:
            strategy_file (str): Path to the JSON file containing strategies
        """
        try:
            with open(strategy_file, 'r') as f:
                self.strategies = json.load(f)
                
            if not self.strategies:
                print(f"Warning: No camera configurations found in {strategy_file}")
            else:
                print(f"Loaded {len(self.strategies)} camera configurations")
                
            # Ensure default strategy exists
            if self.default_strategy not in self.strategies:
                if self.strategies:
                    self.default_strategy = list(self.strategies.keys())[0]
                    print(f"Default camera configuration not found, using '{self.default_strategy}' instead")
                else:
                    print("Warning: No strategies available")
                    
        except FileNotFoundError:
            print(f"Warning: Camera configuration file {strategy_file} not found")
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON format in {strategy_file}")
            self.strategies = {}
            
    def get_strategy(self, strategy_name=None):
        """
        Get a specific strategy by name or the default strategy if none specified.
        
        Args:
            strategy_name (str, optional): Name of the strategy to retrieve
            
        Returns:
            dict: Strategy parameters or empty dict if strategy not found
        """
        if strategy_name is None:
            strategy_name = self.default_strategy
            
        return self.strategies.get(strategy_name, {})
        
    def get_strategy_names(self):
        """
        Get a list of all available strategy names.
        
        Returns:
            list: List of strategy names
        """
        return list(self.strategies.keys())
        
    def get_default_strategy_name(self):
        """
        Get the name of the default strategy.
        
        Returns:
            str: Name of the default strategy
        """
        return self.default_strategy
        
    def set_default_strategy(self, strategy_name):
        """
        Set the default strategy.
        
        Args:
            strategy_name (str): Name of the strategy to set as default
            
        Returns:
            bool: True if successful, False if strategy not found
        """
        if strategy_name in self.strategies:
            self.default_strategy = strategy_name
            return True
        return False
