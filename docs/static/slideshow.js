$(document).ready(function () {

    var pos = 0;
    var max = $("#hint_content").children().length-1;
    function updateHintDisplay(pos, max) {
        if(pos-1==0) $("#prev").animate({ opacity: 100 }).removeClass("buttondisabled")
        if(pos+1==max) $("#next").animate({ opacity: 100 }).removeClass("buttondisabled")
        if(pos==0) $("#prev").animate({ opacity: 0 }).addClass("buttondisabled")
        if(pos==max) $("#next").animate({ opacity: 0 }).addClass("buttondisabled")
        $("#hintdisplay").hide().html($("#hint_content").children().eq(pos).children().slice(1).clone()).fadeIn("fast");
        $("#hinttitle").hide().html($("#hint_content").children().eq(pos).children().eq(0).html()).fadeIn("fast");
    }

    updateHintDisplay(pos)
    $('#prev').on('click', function () {
        if (pos > 0) {
            pos--;
            updateHintDisplay(pos, max);
        }
    });

    $('#next').on('click', function () {
        if (pos < $("#hint_content").children().length - 1) {
            pos++;
            updateHintDisplay(pos, max);
        } 
        
    });
})