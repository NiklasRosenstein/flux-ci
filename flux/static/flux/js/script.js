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

	$('#action-new-build').click(function (event) {
		event.preventDefault();
		event.stopPropagation();
		let caller = $(this);
		let field = $('#input-dialog .input-text')[0];
		$('#input-dialog .input-message').text('Specify a Git ref to check out and build:');
		$('#input-dialog .input-cancel').off('click');
		$('#input-dialog .input-cancel').click(function (event) {
			field.value = '';
			toggleInputDialog();
		});
		$('#input-dialog .input-ok').off('click');
		$('#input-dialog .input-ok').click(function (event) {
			event.preventDefault();
			event.stopPropagation();
			toggleInputDialog();
			let input = field.value;
			field.value = '';
			if (input.length > 0) {
				let repoId = caller.attr('data-repository')
				let url = '/build?repo_id=' + repoId + '&ref=' + input;
				window.location = url;
			}
		});
		toggleInputDialog()
		field.focus();
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


});