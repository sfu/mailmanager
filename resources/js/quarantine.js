/* quarantine.js: javascript code in support of the Quarantine queue management web app
 * Author: Steve Hillman <hillman@sfu.ca>
 */

var action;

var baseUrl = window.location.protocol + "//" + window.location.hostname + window.location.pathname

$(function() {
    $(document).bind("ajaxSend", function() {
        $("#spinner").show();
    }).bind("ajaxStop", function() {
        $("#spinner").hide();
    }).bind("ajaxError", function() {
        $("#spinner").hide();
    });

    // Add UI styles to our elements
	$('input').addClass("ui-widget ui-widget-content ui-corner-all");
	$(".qbutton").button();

	// Add event handlers to our buttons to submit the form
	$(".qbutton").click(function() {
		action = this.id;
        // button ID is the action to perform
		$("#cmd").val(action);
        var needsFilter = action.match(/_[sha]$/);
        // if the action is to release/delete based on sender or hostname, generate list of selected
        // messages to build the filter from
        if (needsFilter) {
            var re=/\./g;
            var selected = [];
            var filterType = "_sender";
            if (needsFilter == "_h") {
                filterType = "_host"
            }
            if (needsFilter == "_a") {
                filterType = "_authuser"
            }
            // collect values from all selected messages
            // get the ID of each checked box, append the filter type (_sender or _host),
            // then retrieve the value of the span with that ID and add it to the values
            $(".messageSelector:checked").each( function() {
                selected.push($("#"+this.id.replace(re,"\\.")+filterType).text());
            });
            $("#filterOn").val(selected.join(";"));
        }
		$("#messageForm").submit();
	});

    // make the rate limiter info dialogue exandable
    $(".expander").click(function(){
        $(".milter-info").slideToggle();
    })

	// Initialize the msg viewer popup
    $("#msg-overlay").popup({
        opacity: 0.5,
        outline: true
    });

    // fetch the quarantine msg list on page load
    refreshMessageList();
 
});

function refreshMessageList() {
    var uniqueusers = ""
    if ($("#uniqueusers").is(":checked"))
    {
        var unique = "&uniqueusers=1"
    }

    $("#messageContainer").load(baseUrl + "?cmd=getqueue" + unique);
}

// Run after the message list loads to hook it into jQuery and add CSS
function setMsgListCSS() {
	// grey the msg we're hovering over
	$(".messageList").hover(function() {
		$(this).css("background-color","LightGrey")
	}, function() {
		$(this).css("background-color","White")
	});

	$('input[type="checkbox"]').shiftSelectable();

	$(".viewmsg").click(function() {
        viewMsg(this.id);
    });
}

// Support shift-click to select multiple messages

$.fn.shiftSelectable = function() {
    var lastChecked,n 
        $boxes = this;

    $boxes.click(function(evt) {
        if(!lastChecked) {
            lastChecked = this;
            return;
        }

        if(evt.shiftKey) {
            var start = $boxes.index(this),
                end = $boxes.index(lastChecked);
            $boxes.slice(Math.min(start, end), Math.max(start, end) + 1)
                .prop('checked', lastChecked.checked)
                .trigger('change');
        }

        lastChecked = this;
    });
};

// Handle opening the msg viewer popup when a msg is clicked on

function viewMsg(msgid) {
	$("#msg-overlay").popup('show');
	$("#msg-overlay-content").load(baseUrl + "?cmd=view&msgid="+msgid);
}
