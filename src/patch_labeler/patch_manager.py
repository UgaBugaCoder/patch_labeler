class PatchManager:
    """Управление состояниями патчей."""
    
    def __init__(self, patches, image_name, data_manager):
        self.patches = patches
        self.image_name = image_name
        self.data_manager = data_manager
        self._init_states()
    
    def _init_states(self):
        """Инициализирует состояния патчей из JSON."""
        saved_patches = self.data_manager.get_image_patches(self.image_name)
        
        for patch in self.patches:
            row, col = patch["index"]
            key = f"{row}_{col}"
            
            class_name = saved_patches.get(key)
            if class_name is not None:
                patch["state"] = "labeled"
                patch["class"] = class_name
            else:
                patch["state"] = "unlabeled"
                patch["class"] = None
    
    def get_selected_patches(self):
        """Возвращает список выделенных патчей."""
        return [p for p in self.patches if p["state"] == "selected"]
    
    def get_labeled_patches(self):
        """Возвращает список размеченных патчей."""
        return [p for p in self.patches if p["state"] == "labeled"]
    
    def toggle_patch(self, patch):
        """Переключает состояние патча при одиночном клике."""
        if patch["state"] == "unlabeled":
            patch["state"] = "selected"
        elif patch["state"] == "selected":
            # Если есть класс → возвращаем в labeled, иначе → unlabeled
            if patch["class"] is not None:
                patch["state"] = "labeled"
            else:
                patch["state"] = "unlabeled"
        elif patch["state"] == "labeled":
            patch["state"] = "selected"
            # class сохраняется
    
    def select_patch(self, patch):
        """Выделяет патч (для кисти в режиме выделения)."""
        if patch["state"] == "unlabeled":
            patch["state"] = "selected"
    
    def deselect_patch(self, patch):
        """Снимает выделение с патча (для кисти в режиме ластика)."""
        if patch["state"] == "selected":
            # Если есть класс → возвращаем в labeled, иначе → unlabeled
            if patch["class"] is not None:
                patch["state"] = "labeled"
            else:
                patch["state"] = "unlabeled"
    
    def clear_selection(self):
        """Снимает выделение: selected с классом → labeled, selected без класса → unlabeled."""
        for patch in self.patches:
            if patch["state"] == "selected":
                if patch["class"] is not None:
                    patch["state"] = "labeled"
                else:
                    patch["state"] = "unlabeled"
    
    def clear_labeling(self):
        """Снимает выделение И класс со всех выделенных патчей."""
        for patch in self.patches:
            if patch["state"] == "selected":
                patch["state"] = "unlabeled"
                patch["class"] = None
    
    def assign_class(self, class_name):
        """Присваивает класс всем выделенным патчам."""
        selected = self.get_selected_patches()
        
        # Проверка: нет ли уже размеченных патчей среди выделенных
        for patch in selected:
            if patch["class"] is not None:
                return False
        
        # Присваиваем класс всем выделенным
        for patch in selected:
            patch["state"] = "labeled"
            patch["class"] = class_name
        
        return True
    
    def save_to_json(self):
        """Сохраняет текущую разметку в JSON через DataManager."""
        patches_dict = {}
        for patch in self.patches:
            row, col = patch["index"]
            key = f"{row}_{col}"
            patches_dict[key] = patch["class"] if patch["state"] == "labeled" else None
        
        self.data_manager.set_image_patches(self.image_name, patches_dict)
        
        labeled_count = len(self.get_labeled_patches())
        total_count = len(self.patches)
        
        if labeled_count == 0:
            status = "none"
        elif labeled_count == total_count:
            status = "full"
        else:
            status = "partly"
        
        self.data_manager.set_image_status(self.image_name, status)
        self.data_manager.save_labels()
    
    def get_statistics(self):
        """Возвращает статистику по текущему снимку."""
        stats = {
            "total": len(self.patches),
            "labeled": 0,
            "classes": {}
        }
        
        for patch in self.patches:
            if patch["state"] == "labeled":
                stats["labeled"] += 1
                class_name = patch["class"]
                stats["classes"][class_name] = stats["classes"].get(class_name, 0) + 1
        
        return stats