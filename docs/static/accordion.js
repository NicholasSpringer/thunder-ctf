var acc = document.getElementsByClassName("accordion");
var i;

for (i = 0; i < acc.length; i++) {
    acc[i].addEventListener("click", function() {
        var panel = this.nextElementSibling;
        var prevActive = this.previousElementSibling.previousElementSibling.classList.contains("active") || this.textContent=="Hint 1";
        if (panel.style.display === "block") {
            this.classList.toggle("active");
            panel.style.display = "none";
        } else if(prevActive){
            this.classList.toggle("active");
            panel.style.display = "block";
        }
    });
}