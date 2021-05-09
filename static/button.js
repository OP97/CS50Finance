$(document).ready(function() {
    $("button").click(function() {
        var action = $(this).data("action"); // get button's action
        var buttonDataId = $(this).data("id"); // get button's data id to use it for form's id

        if (action == "sell") {
                document.getElementById(buttonDataId).action = "/sell"; // change form's action to sell
                // document.getElementById("alertId").style.display = "block";
                // document.getElementById("alertContentId").innerHTML = "You sold " +share_quantity + " amount of shares!";
        } else if (action == "buy") {
                document.getElementById(buttonDataId).action = "/buy"; // change form's action to buy
        }
    });
});