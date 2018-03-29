$(document).ready(function() {
	$('header nav .collapse-button').click(function (event) {
		event.preventDefault();
		event.stopPropagation();
		$('header nav ul').toggle();
	});

	$('.messages .close').click(function (event) {
		event.preventDefault();
		event.stopPropagation();
		$(this).parent('.messages').hide();
	});

	$('[data-confirmation]').click(function(event) {
		event.preventDefault();
		event.stopPropagation();
		$('#confirm-dialog .confirm-message').text($(this).attr('data-confirmation'));
		$('#confirm-dialog .confirm-yes').off('click');
		$('#confirm-dialog .confirm-yes').click(confirmationYes($(this)));
		toggleConfirmDialog();
	});

	$('#confirm-dialog .confirm-no').click(function (event) {
		event.preventDefault();
		event.stopPropagation();
		toggleConfirmDialog();
	});

	function confirmationYes(caller) {
		return function(event) {
			event.preventDefault();
			event.stopPropagation();
			toggleConfirmDialog();
			if (caller.is('[href]')) {
				window.location = caller.attr('href');
			} else if (caller.is('button')) {
				caller.parent('form').submit();
			}
		};
	}

	function toggleConfirmDialog() {
		if ($('header').hasClass('blur')) {
			$('header').removeClass('blur');
			$('main').removeClass('blur');
			$('footer').removeClass('blur');
			$('#confirm-dialog').hide();
			$('#confirm-overlay').hide();
		} else {
			$('header').addClass('blur');
			$('main').addClass('blur');
			$('footer').addClass('blur');
			$('#confirm-dialog').show();
			$('#confirm-overlay').show();
		}
	}

	$('.dropdown').click(function(event){
		event.preventDefault();
		event.stopPropagation();
		$(this).parent().find('.dropdown-menu').toggle();
	});

	$(':not(.dropdown)').click(function(event) {
		$('.dropdown-menu').hide();
	});


});