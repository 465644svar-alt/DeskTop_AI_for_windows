# НАЗНАЧЕНИЕ ФАЙЛА: Сервис управления ветками/режимами выполнения и связанной логикой состояния.
"""
Conversation Branch Manager
Save, load, switch between conversation branches
"""

import os  # ПОЯСНЕНИЕ: импортируется модуль os.
import json  # ПОЯСНЕНИЕ: импортируется модуль json.
import logging  # ПОЯСНЕНИЕ: импортируется модуль logging.
from datetime import datetime  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.
from typing import Dict, List, Optional  # ПОЯСНЕНИЕ: импортируются внешние зависимости для работы модуля.

logger = logging.getLogger(__name__)  # ПОЯСНЕНИЕ: обновляется значение переменной logger.


# ЛОГИЧЕСКИЙ БЛОК: класс `ConversationBranchManager` — объединяет состояние и поведение подсистемы.
class ConversationBranchManager:  # ПОЯСНЕНИЕ: объявляется класс ConversationBranchManager.
    """Manager for conversation branches (save/load/switch/delete)"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.

    # ЛОГИЧЕСКИЙ БЛОК: функция `__init__` — выполняет отдельный шаг бизнес-логики.
    def __init__(self, save_dir: str = "branches"):  # ПОЯСНЕНИЕ: объявляется функция __init__ с параметрами из сигнатуры.
        """Описание: функция `__init__`."""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        self.save_dir = save_dir  # ПОЯСНЕНИЕ: обновляется значение переменной self.save_dir.
        self.branches_file = os.path.join(save_dir, "branches.json")  # ПОЯСНЕНИЕ: обновляется значение переменной self.branches_file.
        self.branches: List[dict] = []  # ПОЯСНЕНИЕ: обновляется значение переменной self.branches: List[dict].
        self.current_branch_id: Optional[str] = None  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_id: Optional[str].
        os.makedirs(save_dir, exist_ok=True)  # ПОЯСНЕНИЕ: обновляется значение переменной os.makedirs(save_dir, exist_ok.
        self._load_branches_index()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_load_branches_index` — выполняет отдельный шаг бизнес-логики.
    def _load_branches_index(self):  # ПОЯСНЕНИЕ: объявляется функция _load_branches_index с параметрами из сигнатуры.
        """Load branches index from file"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if os.path.exists(self.branches_file):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                with open(self.branches_file, 'r', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                    data = json.load(f)  # ПОЯСНЕНИЕ: обновляется значение переменной data.
                    self.branches = data.get("branches", [])  # ПОЯСНЕНИЕ: обновляется значение переменной self.branches.
                    self.current_branch_id = data.get("current_branch_id")  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_id.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            logger.error(f"Failed to load branches index: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            self.branches = []  # ПОЯСНЕНИЕ: обновляется значение переменной self.branches.

    # ЛОГИЧЕСКИЙ БЛОК: функция `_save_branches_index` — выполняет отдельный шаг бизнес-логики.
    def _save_branches_index(self):  # ПОЯСНЕНИЕ: объявляется функция _save_branches_index с параметрами из сигнатуры.
        """Save branches index to file"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            with open(self.branches_file, 'w', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                json.dump({  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    "branches": self.branches,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    "current_branch_id": self.current_branch_id  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                }, f, ensure_ascii=False, indent=2)  # ПОЯСНЕНИЕ: обновляется значение переменной }, f, ensure_ascii.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            logger.error(f"Failed to save branches index: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

    # ЛОГИЧЕСКИЙ БЛОК: функция `create_branch` — выполняет отдельный шаг бизнес-логики.
    def create_branch(  # ПОЯСНЕНИЕ: объявляется функция create_branch с параметрами из сигнатуры.
        self,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        name: str,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        providers_history: Dict[str, List[dict]],  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        chat_content: str = ""  # ПОЯСНЕНИЕ: обновляется значение переменной chat_content: str.
    ) -> str:  # ПОЯСНЕНИЕ: начинается новый логический блок кода.
        """Create a new branch from current state"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        branch_id = datetime.now().strftime("%Y%m%d_%H%M%S_") + str(len(self.branches))  # ПОЯСНЕНИЕ: обновляется значение переменной branch_id.

        branch = {  # ПОЯСНЕНИЕ: обновляется значение переменной branch.
            "id": branch_id,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "name": name,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "created_at": datetime.now().isoformat(),  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "message_count": sum(len(h) for h in providers_history.values())  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        }  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        # Save branch data to separate file
        branch_data = {  # ПОЯСНЕНИЕ: обновляется значение переменной branch_data.
            "id": branch_id,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "name": name,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "created_at": branch["created_at"],  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "providers_history": providers_history,  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            "chat_content": chat_content  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        }  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        branch_file = os.path.join(self.save_dir, f"branch_{branch_id}.json")  # ПОЯСНЕНИЕ: обновляется значение переменной branch_file.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            with open(branch_file, 'w', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                json.dump(branch_data, f, ensure_ascii=False, indent=2)  # ПОЯСНЕНИЕ: обновляется значение переменной json.dump(branch_data, f, ensure_ascii.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            logger.error(f"Failed to save branch data: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return ""  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

        self.branches.append(branch)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        self.current_branch_id = branch_id  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_id.
        self._save_branches_index()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

        return branch_id  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `load_branch` — выполняет отдельный шаг бизнес-логики.
    def load_branch(self, branch_id: str) -> Optional[dict]:  # ПОЯСНЕНИЕ: объявляется функция load_branch с параметрами из сигнатуры.
        """Load branch data by ID"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        branch_file = os.path.join(self.save_dir, f"branch_{branch_id}.json")  # ПОЯСНЕНИЕ: обновляется значение переменной branch_file.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if os.path.exists(branch_file):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                with open(branch_file, 'r', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                    data = json.load(f)  # ПОЯСНЕНИЕ: обновляется значение переменной data.
                    self.current_branch_id = branch_id  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_id.
                    self._save_branches_index()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
                    return data  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            logger.error(f"Failed to load branch: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
        return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `delete_branch` — выполняет отдельный шаг бизнес-логики.
    def delete_branch(self, branch_id: str) -> bool:  # ПОЯСНЕНИЕ: объявляется функция delete_branch с параметрами из сигнатуры.
        """Delete a branch"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        branch_file = os.path.join(self.save_dir, f"branch_{branch_id}.json")  # ПОЯСНЕНИЕ: обновляется значение переменной branch_file.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if os.path.exists(branch_file):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                os.remove(branch_file)  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

            self.branches = [b for b in self.branches if b["id"] != branch_id]  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if self.current_branch_id == branch_id:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                self.current_branch_id = None  # ПОЯСНЕНИЕ: обновляется значение переменной self.current_branch_id.

            self._save_branches_index()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return True  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
        except Exception as e:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
            logger.error(f"Failed to delete branch: {e}")  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
            return False  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_branches_list` — выполняет отдельный шаг бизнес-логики.
    def get_branches_list(self) -> List[dict]:  # ПОЯСНЕНИЕ: объявляется функция get_branches_list с параметрами из сигнатуры.
        """Get list of all branches"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        return self.branches.copy()  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `rename_branch` — выполняет отдельный шаг бизнес-логики.
    def rename_branch(self, branch_id: str, new_name: str) -> bool:  # ПОЯСНЕНИЕ: объявляется функция rename_branch с параметрами из сигнатуры.
        """Rename a branch"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for branch in self.branches:  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if branch["id"] == branch_id:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                branch["name"] = new_name  # ПОЯСНЕНИЕ: обновляется значение переменной branch["name"].
                self._save_branches_index()  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.

                # Update branch file
                branch_file = os.path.join(self.save_dir, f"branch_{branch_id}.json")  # ПОЯСНЕНИЕ: обновляется значение переменной branch_file.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                try:  # ПОЯСНЕНИЕ: начинается блок перехвата возможных ошибок.
                    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
                    if os.path.exists(branch_file):  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                        with open(branch_file, 'r', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                            data = json.load(f)  # ПОЯСНЕНИЕ: обновляется значение переменной data.
                        data["name"] = new_name  # ПОЯСНЕНИЕ: обновляется значение переменной data["name"].
                        with open(branch_file, 'w', encoding='utf-8') as f:  # ПОЯСНЕНИЕ: открывается контекстный менеджер для ресурса.
                            json.dump(data, f, ensure_ascii=False, indent=2)  # ПОЯСНЕНИЕ: обновляется значение переменной json.dump(data, f, ensure_ascii.
                # ЛОГИЧЕСКИЙ БЛОК: обработка ошибок и устойчивость выполнения.
                except Exception:  # ПОЯСНЕНИЕ: обрабатывается ошибка в блоке except.
                    pass  # ПОЯСНЕНИЕ: оставляется пустая заглушка без действий.
                return True  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        return False  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.

    # ЛОГИЧЕСКИЙ БЛОК: функция `get_branch_by_id` — выполняет отдельный шаг бизнес-логики.
    def get_branch_by_id(self, branch_id: str) -> Optional[dict]:  # ПОЯСНЕНИЕ: объявляется функция get_branch_by_id с параметрами из сигнатуры.
        """Get branch info by ID"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
        # ЛОГИЧЕСКИЙ БЛОК: цикл для поэтапной обработки данных.
        for branch in self.branches:  # ПОЯСНЕНИЕ: запускается цикл for по коллекции.
            # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
            if branch["id"] == branch_id:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
                return branch.copy()  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
        return None  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.


# Singleton instance
_branch_manager_instance: Optional[ConversationBranchManager] = None  # ПОЯСНЕНИЕ: обновляется значение переменной _branch_manager_instance: Optional[ConversationBra.


# ЛОГИЧЕСКИЙ БЛОК: функция `get_branch_manager` — выполняет отдельный шаг бизнес-логики.
def get_branch_manager(save_dir: str = "branches") -> ConversationBranchManager:  # ПОЯСНЕНИЕ: объявляется функция get_branch_manager с параметрами из сигнатуры.
    """Get or create branch manager instance"""  # ПОЯСНЕНИЕ: задается или продолжается строка документации.
    global _branch_manager_instance  # ПОЯСНЕНИЕ: выполняется текущая инструкция этого шага логики.
    # ЛОГИЧЕСКИЙ БЛОК: ветвление условий для выбора дальнейшего сценария.
    if _branch_manager_instance is None:  # ПОЯСНЕНИЕ: проверяется условие ветвления if.
        _branch_manager_instance = ConversationBranchManager(save_dir)  # ПОЯСНЕНИЕ: обновляется значение переменной _branch_manager_instance.
    return _branch_manager_instance  # ПОЯСНЕНИЕ: возвращается результат из текущей функции.
