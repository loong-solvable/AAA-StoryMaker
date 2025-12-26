
import sys
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from agents.online.layer3.screen_agent import ScreenAgent, ScreenInput

class TestScreenAgentOptimization(unittest.TestCase):
    def setUp(self):
        self.agent = ScreenAgent(world_name="TestWorld")
        # Mock LLM chains to avoid actual API calls
        self.agent.chain = MagicMock()
        self.agent.script_chain = MagicMock()
        self.agent.script_chain.invoke.return_value = '{"visual_render_data": {"summary": "test"}}'
        self.agent.chain.invoke.return_value = '{"visual_render_data": {"summary": "fallback"}}'
        
        # Mock file operations
        self.agent.save_visual_data = MagicMock()

    def test_render_with_script_content(self):
        """Test render with script content (scene_start)"""
        input_data = ScreenInput(
            scene_id=1,
            script_content="Full script content here...",
            world_state={"location": {"name": "Test Loc"}}
        )
        
        # Call render with generate_visual=True
        self.agent.render(input_data, render_terminal=False, generate_visual=True, save_json=True)
        
        # Verify script_chain was called
        self.agent.script_chain.invoke.assert_called_once()
        # Verify normal chain was NOT called
        self.agent.chain.invoke.assert_not_called()
        # Verify save_visual_data was called
        self.agent.save_visual_data.assert_called_once()

    def test_render_without_script_content(self):
        """Test render without script content (fallback logic)"""
        input_data = ScreenInput(
            scene_id=1,
            world_state={"location": {"name": "Test Loc"}}
        )
        
        # Call render with generate_visual=True
        self.agent.render(input_data, render_terminal=False, generate_visual=True, save_json=True)
        
        # Verify script_chain was NOT called
        self.agent.script_chain.invoke.assert_not_called()
        # Verify normal chain was called (fallback)
        self.agent.chain.invoke.assert_called_once()

    def test_render_no_visual_generation(self):
        """Test render with generate_visual=False (dialogue turn)"""
        input_data = ScreenInput(
            scene_id=1,
            script_content="Full script content here...", # Even if present
            world_state={"location": {"name": "Test Loc"}}
        )
        
        # Call render with generate_visual=False
        self.agent.render(input_data, render_terminal=False, generate_visual=False, save_json=False)
        
        # Verify NO chains were called
        self.agent.script_chain.invoke.assert_not_called()
        self.agent.chain.invoke.assert_not_called()
        # Verify save_visual_data was NOT called
        self.agent.save_visual_data.assert_not_called()

if __name__ == '__main__':
    unittest.main()
