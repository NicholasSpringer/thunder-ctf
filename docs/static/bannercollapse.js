$(function () {
    $(window).scroll(function () {

        var winTop = $(this).scrollTop();
        $("header").css("height", 190 - winTop)
    });
});