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

	$('[data-input-callback]').click(function (event) {
		event.preventDefault();
		event.stopPropagation();
		var caller = $(this);
		var field = $('#input-dialog .input-text');
		var inputText = caller.attr('data-input-text');
		field.val(inputText !== undefined ? inputText : '');
		if (field.val() !== '') {
			field[0].select();
		}

		$('#input-dialog .input-message').text($(this).attr('data-input-message'));
		$('#input-dialog .input-cancel').off('click');
		$('#input-dialog .input-cancel').click(function (event) {
			field.val('');
			toggleInputDialog();
		});
		$('#input-dialog .input-ok').off('click');
		$('#input-dialog .input-ok').click(function (event) {
			event.preventDefault();
			event.stopPropagation();
			toggleInputDialog();
			var input = field.val();
			field.val('');
			var callback = caller.attr('data-input-callback');
			eval(callback)(input);
		});
		toggleInputDialog();
		field[0].focus();
	});

	$('#confirm-dialog .confirm-no').click(function (event) {
		event.preventDefault();
		event.stopPropagation();
		toggleConfirmDialog();
	});

	$('#input-dialog .input-text').on('keyup', function(event) {
		if (event !== undefined && event.keyCode === 13) {
			$('#input-dialog .input-ok').click();
		} else if (event !== undefined && event.keyCode === 27) {
			$('#input-dialog .input-cancel').click();
		}
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

	function toggleInputDialog() {
		if ($('header').hasClass('blur')) {
			$('header').removeClass('blur');
			$('main').removeClass('blur');
			$('footer').removeClass('blur');
			$('#input-dialog').hide();
			$('#input-overlay').hide();
		} else {
			$('header').addClass('blur');
			$('main').addClass('blur');
			$('footer').addClass('blur');
			$('#input-dialog').show();
			$('#input-overlay').show();
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

	$('.upload-form input[type=file]').on('change', function() {
		if ('files' in $(this)[0]) {
			if ($(this)[0].files.length > 0) {
				$(this).parent('.upload-form').submit();
			}
		}
	});

	$('[data-toggle]').click(function(event) {
		event.preventDefault();
		event.stopPropagation();
		var id = $(this).attr('data-toggle');
		$(id).toggle();
	});
});