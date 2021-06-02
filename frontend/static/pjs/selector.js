$(document).ready(function(){

    //CHECKBOX
    $.each($('.checkbox'),function(index,val) {
        if($(this).find('input').prop('checked')==true){
            $(this).addClass('active');
        }
    });
    $(document).on('click','.checkbox', function(event) {
        if($(this).hasClass('active')){
            $(this).find('input').prop('checked',false);
        }else{
            $(this).find('input').prop('checked',true);
        }
        $(this).toggleClass('active');

        return false;
    });

    //RADIO 
    $.each($('.radiobuttons__item'),function(index,val) {
        if($(this).find('input').prop('checked')==true){
            $(this).addClass('active');
        }
    });
    $(document).on('click','.radiobuttons__item', function(event) {
        $(this).parents('.radiobuttons').find('.radiobuttons__item').removeClass('active');
        $(this).parents('.radiobuttons').find('.radiobuttons__item input').prop('checked', false);
        $(this).toggleClass('active');
        $(this).find('input').prop('checked',true);
        return false;
    });


    //RADIO CALCULATION OBJECT
    $.each($('.radioobj__item'),function(index,val) {
        if($(this).find('input').prop('checked')==true){
            $(this).addClass('active');
        }
    });
    $(document).on('click','.radioobj__item', function(event) {
        $(this).parents('.radiobuttons').find('.radioobj__item').removeClass('active');
        $(this).parents('.radiobuttons').find('.radioobj__item input').prop('checked', false);
        $(this).toggleClass('active');
        $(this).find('input').prop('checked',true);
        return false;
    });
});


//MULTIPLE SELECTOR

