jQuery(($) => {

    // Уменьшаем на 1 
    $(document).on('click', '.mh-input__bottom', function () {
        let total = $(this).prev().prev();
        if ( total.val() > 1 ) {
            total.val(+total.val() - 1);
        }
    });

    // Увеличиваем на 1 
    $(document).on('click', '.mh-input__top', function () {
        let total = $(this).prev();
        total.val(+total.val() + 1);
    });

        // Уменьшаем на 1 
        $(document).on('click', '.hh-input__bottom', function () {
            let total = $(this).prev().prev();
            if ( total.val() > 1 ) {
                total.val(+total.val() - 1);
            }
        });
    
        // Увеличиваем на 1 
        $(document).on('click', '.hh-input__top', function () {
            let total = $(this).prev();
            total.val(+total.val() + 1);
        });
    


});