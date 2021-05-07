$(document).ready(function() {
    $("button").click(function() {
        var share_quantity = document.getElementById("share_quantity").value; // get the quantity
        var action = $(this).data('action'); // get button's action


        if (action == "sell") {
            if (share_quantity > 0) {
                document.getElementById("action_form").action = "/sell"; // change form's action to sell
            } else {
                alert("Enter a valid value");
            }

        } else if (action == "buy") {
            if (share_quantity > 0) {
                document.getElementById("action_form").action = "/buy"; // change form's action to buy
            }
        } else {
            alert("Enter a valid value");
        }
    });
});