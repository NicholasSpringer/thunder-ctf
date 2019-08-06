var acc = document.getElementsByClassName("accordion");
var i;

for (i = 0; i < acc.length; i++) {
    acc[i].addEventListener("click", function() {
        var panel = this.nextElementSibling;
        if(this.classList.contains("active")) {
            this.classList.remove("active");
            panel.style.display = "none";
        } else {
            var allowOpen = this.previousElementSibling.previousElementSibling.classList.contains("prevActive") || this.textContent=="Hint 1";
            if(allowOpen) {
                if(!this.classList.contains("prevActive")){
                    this.classList.add("prevActive");
                }
                this.classList.add("active");
                panel.style.display = "block";
            } 
        }
    })
}