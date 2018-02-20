# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

task_config = {}

"""A short and descriptive title about the kind of task the HIT contains.
On the Amazon Mechanical Turk web site, the HIT title appears in search results,
and everywhere the HIT is mentioned.
"""
task_config['hit_title'] = 'Detect common and different images by chatting with another player'


"""A description includes detailed information about the kind of task the HIT contains.
On the Amazon Mechanical Turk web site, the HIT description appears in the expanded
view of search results, and in the HIT and assignment screens.
"""
task_config['hit_description'] = \
'''
You will have a conversation with another player to find out which of the six images on your display are 
shown to the both of you. Try to be as fast as possible! \n
You can directly mark an image in the interface. A full game consists of five rounds with the same matched player
and will take about 15 minutes.
'''

"""One or more words or phrases that describe the HIT, separated by commas.
On MTurk website, these words are used in searches to find HITs.
"""
task_config['hit_keywords'] = 'chat, dialog, goal-oriented, multi-round, visually-grounded'


"""A detailed task description that will be shown on the HIT task game_window page
and on the left side of the chat page. Supports HTML formatting.
"""
task_config['task_description'] = \
'''
<div id='preview'>
You will have a conversation with another player to find out which of the six images on your display are 
shown to the both of you. Try to be as fast as possible! \n
You can directly mark an image in the interface. A full game consists of five rounds with the same matched player
and will take about 15 minutes.

If you are ready, please click "Accept HIT" to start this task.
</div>
<div id='test'></div>
<div id='game_window'></div>

<script src="https://ajax.googleapis.com/ajax/libs/jquery/3.2.1/jquery.min.js"></script>

<script type="text/javascript">

	$(document).ready(function(){
        required = function(fields) {
                var valid = true;
            fields.each(function () { // iterate all
                var $this = $(this);
                if (($this.is(':checkbox') && !$this.is(":checked")) || // checkbox
                    (($this.is(':text') || $this.is('textarea')) && !$this.val()) || // text and textarea
                    ($this.is(':radio') && !$('input[name='+ $this.attr("name") +']:checked').length)) { // radio
                    valid = false;
            }
        });
            return valid;
        }
    
        validateRealTime = function () {
            var fields = $("form :input:not(:hidden)"); // select required
            fields.on('keyup change keypress blur', function () {
                if (required(fields)) {
                    {document.getElementById("image_selection").disabled = false;} // action if all valid
                } else {
                    {document.getElementById("image_selection").disabled = true;} // action if not valid
                }
            });
        }
        validateRealTime();
    });

</script>

<style>
	div.gallery {
		margin: 5px;
		border: 1px solid #ccc;
		float: left;
		width: 250px;
	}

	div.cover {
		background-size: cover;
		background-repeat: no-repeat;
		background-position: center center;
		border: 1px solid;
		width: 250px;
		height: 167px;
	}

	div.desc {
		padding-top: 10px;
		padding-bottom: 10px;
		text-align: center;
		width: 250px;
	}
</style>

<script type="text/javascript">

    var git_path = "https://raw.githubusercontent.com/janoschhaber/psivgd/master/";
    
    var your_selection = "";
    var their_selection = "";
    
    var num_messages = 0;
    
    var round_counter = 0;


	function makeInput(images) {
	
		$('#preview').html("");

		$('#game_window').html("");
		var display = $('#game_window');

		var string = '<form id="image_selection_form">';
		
        for (var image_id in images) {         
            var image_path = images[image_id];
        
            string += '<div class="gallery"><div class="cover" style="background-image: url(';
            string += git_path + image_path;
            string += ');"> </div> <div class="desc" ';
            string += 'id="';
            string += escapeHtml(image_path).replace(/\D/g,'');
            string += '"> <input type="radio" id="';
            string += String(image_id);
            string += '_common" name="';
            string += String(image_id);
            string += '" value="common" '
            
            string += 'onclick="validateRealTime(); '            
            // string += 'sendSelectionMessage(&apos;ID&apos;, &apos;<com>&apos;);"'
            
            string += 'sendSelectionMessage(&apos;<com>&apos;, &apos;' 
            string += image_path 
            string += '&apos;);"' 
            
            string += '> Common <input type="radio" id="';
            string += String(image_id);
            string += '_different" name="';
            string += String(image_id);
            string += '" value="different" '
            
            string += 'onclick="validateRealTime(); '            
            //string += 'onclick="sendSelectionMessage(&apos;ID&apos;, &apos;<dif>&apos;);"'
            
            string += 'sendSelectionMessage(&apos;<dif>&apos;, &apos;' 
            string += image_path 
            string += '&apos;);"'
            
            string += '> Different </div></div>';     
        }
            
        string += ' </form>';
        string += ' <button class="btn btn-primary" style="width: 150px; font-size: 16px; float: left; margin-left: 10px; padding: 10px;" id="image_selection" onclick="getFeedback();" disabled="disabled"> Submit Selection </button>';
        string += ' <button class="btn btn-primary" style="width: 150px; font-size: 16px; float: left; margin-left: 10px; padding: 10px;" id="next_round" onclick="nextRound();"> Next Round </button>';
        string += ' <button class="btn btn-primary" style="width: 150px; font-size: 16px; float: left; margin-left: 10px; padding: 10px;" id="finish" onclick="nextRound();"> Finish </button>';
        
        display.append(string);
        $("button#next_round").hide();
        $("button#finish").hide();
        
    }

	(function() {
    // Override handle_new_message function
    handle_new_message = function() {
        var new_message_id = arguments[0];
        var message = arguments[1];
        var agent_id = message.id;
        var text = message.text;
        var images = message.images;
        var solution = message.solution;
        var was_this_agent = (agent_id == cur_agent_id);
        
        if (displayed_messages.indexOf(new_message_id) !== -1) {
            // This message has already been seen and put up into the chat
            log(new_message_id + ' was a repeat message', 1);
            return;
        }

        log('New message, ' + new_message_id + ' from agent ' + agent_id, 1);
        displayed_messages.push(new_message_id);         

        if (message.images) {
            makeInput(images);
            
            $('#title').html(text.split(' ').slice(0,2).join(' '));    
            // round_counter = int(text.split(' ').slice(1,2).join(' '));
            // $('#test').html(round_counter);
            
            if (num_messages == 0) {
                add_message_to_conversation("INSTRUCTOR", "You are paired with a new player.", false);
                
                var game_header = "Label each image as <i>common</i> or <i>different</i> by chatting with your partner. ";
                game_header += "<b>Please use normal English language and refrain from using abbreviations or code.</b> ";
                game_header += "Also, please don’t just list descriptions of all images in a single message. </br>";
                game_header += "When you identified a common or different image, click the respective checkbox under the image.";
                add_message_to_conversation("INSTRUCTOR", game_header, false);
            }             
                      
            
        } else if (text.startsWith('<selection>')) {
            
        } else if (text.startsWith('<next_round>')) {
                    
        } else if (message.solution) {
            // $('#test').html(escapeHtml('Show Feedback!'));  
            showFeedback(solution);      
        } else {
            num_messages++;

            message.id = (was_this_agent ? "YOU:" : "THEM:");
            var agent_id = message.id;
            add_message_to_conversation(was_this_agent ? "YOU" : "THEM", text, was_this_agent);
        }        
    };
})();

function escapeHtml(unsafe) {
    return unsafe
         .replace(/&/g, "&amp;")
         .replace(/</g, "&lt;")
         .replace(/>/g, "&gt;")
         .replace(/"/g, "&quot;")
         .replace(/'/g, "&#039;");
 }

function sendSelectionMessage(image_id, m_type) {

    var selection = '<selection> ' + String(image_id) + ' ' + String(m_type)
    // $('#test').html(escapeHtml(selection));
    
    new_message_id = uuidv4();     
    send_packet(
        TYPE_MESSAGE,
        {
          text: selection,
          id: cur_agent_id,
          message_id: new_message_id,
          episode_done: false
        },
        true,
        true,
        function(msg) {
        }
      );
}

function showFeedback(solution) {
 
    feedback_msg = '';
   
    for (var item in solution) {    
        var item_id = item[0];
        var tuple = solution[item_id];
        
        var image_path = tuple[0];      
        var mark = tuple[1];
        
        // feedback_msg += String(image_path);
        
        if (mark == 1) {
            feedback_msg += ' was correct. ';  
            var descriptor = escapeHtml(image_path).replace(/\D/g,'');
            $('#' + descriptor).css("background-color", "#A0FF58");
            
        } else {
            feedback_msg += ' was NOT correct. ';
            var descriptor = escapeHtml(image_path).replace(/\D/g,'');
            $('#' + descriptor).css("background-color", "#FF6E65");
        }    
            
    } 
    
    $("button#next_round").show();
}

function getFeedback() {
    // $('#test').html(escapeHtml('Getting Feedback'));  
    new_message_id = uuidv4();  
    $("button#image_selection").hide();     
    send_packet(
        TYPE_MESSAGE,
        {
          text: '<feedback>',
          id: cur_agent_id,
          message_id: new_message_id,
          episode_done: false
        },
        true,
        true,
        function(msg) {
        }
      );
}

function nextRound() {
    // $('#test').html(escapeHtml('Next Round')); 
    new_message_id = uuidv4();   
    $("button#next_round").hide();  
    send_packet(
        TYPE_MESSAGE,
        {
          text: '<next_round>',
          id: cur_agent_id,
          message_id: new_message_id,
          episode_done: false
        },
        true,
        true,
        function(msg) {
        }
      );
}
	
</script>
'''


