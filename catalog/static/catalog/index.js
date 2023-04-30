class CheckboxGroup {
    constructor(checkboxes, controlContainer, controlTitle = 'Select All') {
        this.checkboxes = Array.from(checkboxes)
        this.checkboxes.forEach((el) => el.addEventListener('change', () => this.syncControlState()))

        this.control = document.createElement('input')
        this.control.type = 'checkbox'
        this.control.title = controlTitle
        this.control.addEventListener('change', () => this.control.checked ? this.selectAll() : this.unselectAll())
        controlContainer.appendChild(this.control)
    }
    syncControlState() {
        if (this.checkboxes.length == 0) {
            this.control.indeterminate = false
            this.control.checked = false
            this.control.disabled = true
        } else if (this.allSelected()) {
            this.control.indeterminate = false
            this.control.checked = true
        } else if (this.allUnselected()) {
            this.control.indeterminate = false
            this.control.checked = false
        } else {
            this.control.indeterminate = true
            this.control.checked = false
        }
    }
    selectAll() {
        this.checkboxes.forEach((el) => el.checked = true)
    }
    unselectAll() {
        this.checkboxes.forEach((el) => el.checked = false)
    }
    allSelected() {
        return this.checkboxes.every((el) => el.checked)
    }
    allUnselected() {
        return this.checkboxes.every((el) => !el.checked)
    }
}

const checkboxes = new CheckboxGroup(
    document.querySelectorAll('input[name="book_id"]'),
    document.getElementById('select-column'),
);

checkboxes.syncControlState()
