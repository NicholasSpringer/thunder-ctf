$(document).ready(function () {
    var showWriteup = false;
    var pos = 0;
    var max = $("#hint_content").children().length-1;
    function switchHint() {
        if(pos-1==0) $("#prev").animate({ opacity: 100 }).removeClass("buttondisabled");
        if(pos+1==max) $("#next").animate({ opacity: 100 }).removeClass("buttondisabled");
        if(pos==0) $("#prev").animate({ opacity: 0 }).addClass("buttondisabled");
        if(pos==max) $("#next").animate({ opacity: 0 }).addClass("buttondisabled");
        $("#hint_display").hide().html($("#hint_content").children().eq(pos).children().slice(1).clone()).fadeIn("fast");
        $("#hint_title").hide().html($("#hint_content").children().eq(pos).children().eq(0).html()).fadeIn("fast");
    }

    function toggleWriteup() {
        showWriteup = !showWriteup;
        if(!showWriteup) {
            if(!(pos==0)) $("#prev").animate({ opacity: 100 }).removeClass("buttondisabled");
            if(!(pos==max)) $("#next").animate({ opacity: 100 }).removeClass("buttondisabled");
            switchHint();
            $("#writeup_button").hide().html("Show Level Writeup").fadeIn("fast");
        } else {
            $("#prev").animate({ opacity: 0 }).addClass("buttondisabled")
            $("#next").animate({ opacity: 0 }).addClass("buttondisabled")
            $("#hint_display").hide().html($("#writeup_content").html()).fadeIn("fast");
            $("#hint_title").hide().html("Level Writeup").fadeIn("fast");
            $("#writeup_button").hide().html("Show Level Hints").fadeIn("fast");
        }
    }

    switchHint(pos)
    $('#prev').on('click', function () {
        if (pos > 0) {
            pos--;
            switchHint();
        }
    });

    $('#next').on('click', function () {
        if (pos < $("#hint_content").children().length - 1) {
            pos++;
            switchHint();
        } 
        
    });
    
    $('#writeup_button').on('click', function () {
        toggleWriteup();
    });
})