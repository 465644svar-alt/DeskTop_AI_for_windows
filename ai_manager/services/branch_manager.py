"""
Conversation Branch Manager
Save, load, switch between conversation branches
"""

import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ConversationBranchManager:
    """Manager for conversation branches (save/load/switch/delete)"""

    def __init__(self, save_dir: str = "branches"):
        self.save_dir = save_dir
        self.branches_file = os.path.join(save_dir, "branches.json")
        self.branches: List[dict] = []
        self.current_branch_id: Optional[str] = None
        os.makedirs(save_dir, exist_ok=True)
        self._load_branches_index()

    def _load_branches_index(self):
        """Load branches index from file"""
        try:
            if os.path.exists(self.branches_file):
                with open(self.branches_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.branches = data.get("branches", [])
                    self.current_branch_id = data.get("current_branch_id")
        except Exception as e:
            logger.error(f"Failed to load branches index: {e}")
            self.branches = []

    def _save_branches_index(self):
        """Save branches index to file"""
        try:
            with open(self.branches_file, 'w', encoding='utf-8') as f:
                json.dump({
                    "branches": self.branches,
                    "current_branch_id": self.current_branch_id
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save branches index: {e}")

    def create_branch(
        self,
        name: str,
        providers_history: Dict[str, List[dict]],
        chat_content: str = ""
    ) -> str:
        """Create a new branch from current state"""
        branch_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + str(len(self.branches))

        branch = {
            "id": branch_id,
            "name": name,
            "created_at": datetime.now().isoformat(),
            "message_count": sum(len(h) for h in providers_history.values())
        }

        # Save branch data to separate file
        branch_data = {
            "id": branch_id,
            "name": name,
            "created_at": branch["created_at"],
            "providers_history": providers_history,
            "chat_content": chat_content
        }

        branch_file = os.path.join(self.save_dir, f"branch_{branch_id}.json")
        try:
            with open(branch_file, 'w', encoding='utf-8') as f:
                json.dump(branch_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save branch data: {e}")
            return ""

        self.branches.append(branch)
        self.current_branch_id = branch_id
        self._save_branches_index()

        return branch_id

    def load_branch(self, branch_id: str) -> Optional[dict]:
        """Load branch data by ID"""
        branch_file = os.path.join(self.save_dir, f"branch_{branch_id}.json")
        try:
            if os.path.exists(branch_file):
                with open(branch_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.current_branch_id = branch_id
                    self._save_branches_index()
                    return data
        except Exception as e:
            logger.error(f"Failed to load branch: {e}")
        return None

    def delete_branch(self, branch_id: str) -> bool:
        """Delete a branch"""
        branch_file = os.path.join(self.save_dir, f"branch_{branch_id}.json")
        try:
            if os.path.exists(branch_file):
                os.remove(branch_file)

            self.branches = [b for b in self.branches if b["id"] != branch_id]

            if self.current_branch_id == branch_id:
                self.current_branch_id = None

            self._save_branches_index()
            return True
        except Exception as e:
            logger.error(f"Failed to delete branch: {e}")
            return False

    def get_branches_list(self) -> List[dict]:
        """Get list of all branches"""
        return self.branches.copy()

    def rename_branch(self, branch_id: str, new_name: str) -> bool:
        """Rename a branch"""
        for branch in self.branches:
            if branch["id"] == branch_id:
                branch["name"] = new_name
                self._save_branches_index()

                # Update branch file
                branch_file = os.path.join(self.save_dir, f"branch_{branch_id}.json")
                try:
                    if os.path.exists(branch_file):
                        with open(branch_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        data["name"] = new_name
                        with open(branch_file, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                return True
        return False

    def get_branch_by_id(self, branch_id: str) -> Optional[dict]:
        """Get branch info by ID"""
        for branch in self.branches:
            if branch["id"] == branch_id:
                return branch.copy()
        return None


# Singleton instance
_branch_manager_instance: Optional[ConversationBranchManager] = None


def get_branch_manager(save_dir: str = "branches") -> ConversationBranchManager:
    """Get or create branch manager instance"""
    global _branch_manager_instance
    if _branch_manager_instance is None:
        _branch_manager_instance = ConversationBranchManager(save_dir)
    return _branch_manager_instance
