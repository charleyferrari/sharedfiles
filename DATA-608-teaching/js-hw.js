var dataset;
d3.csv('https://raw.githubusercontent.com/charleyferrari/sharedfiles/master/heightweight.csv', function(data){
    dataset = data;
    var text;
    d3.select('body').selectAll('p')
        .data(dataset)
        .enter()
        .append('p')
        .text(function(d) {
            return d.Name + ' is ' + d.Height + 'cm tall and weighs ' + d.Weight + 'lb.';
        });
});
