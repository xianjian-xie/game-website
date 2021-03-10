$(document).ready(function(){
    $("#global").keyup(function(){
        var val = $(this).val();
        $.get("/autocomplete", {query:val}, function(data){
            $("#list").empty();
            console.log(data)
            for(var i = 0; i < data.length; i++) {
                $("#list").append($("<li>"+data[i]+"</li>"))
            }
        });
    })
});
